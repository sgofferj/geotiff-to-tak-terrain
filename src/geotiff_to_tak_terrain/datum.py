#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# datum.py from https://github.com/sgofferj/geotiff-to-tak-terrain
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Vertical datum handling: convert orthometric/normal heights to ellipsoidal (HAE) and back.

Convention used throughout: h (ellipsoidal, HAE) = H (orthometric/normal) + N (geoid undulation).

Supported input datums (--input-datum):
  - hae:   ellipsoidal heights, no conversion needed for HAE output.
  - msl:   orthometric heights (e.g. EGM96/EGM2008). Convert with EGM geoid grid or offset.
  - n2000: Finnish N2000 normal heights. Convert with FIN2005N00/FIN2023N2000 grid or offset.
  - n60:   Finnish N60 normal heights. Convert with N60 geoid grid or offset.

Supported output datums (--heights):
  - hae (default, what ATAK expects): ellipsoidal heights.
  - msl: orthometric heights.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging
import os
import re
import urllib.request
import numpy as np
from numpy.typing import NDArray
from osgeo import gdal

gdal.UseExceptions()
logger = logging.getLogger(__name__)

INPUT_DATUMS = ("hae", "msl", "n2000", "n60")
#: CLI choices include "auto" for automatic detection.
INPUT_DATUM_CHOICES = ("auto",) + INPUT_DATUMS
OUTPUT_DATUMS = ("hae", "msl")

PROJ_CDN_ENDPOINT = "https://cdn.proj.org"

#: Preferred geoid grids per input datum for conversion to HAE (h = H + N).
#: First entry is the preferred grid; others are fallbacks.
GEOID_GRID_CANDIDATES: Dict[str, List[str]] = {
    "n2000": ["fi_nls_fin2023n2000.tif", "fi_nls_fin2005n00.tif"],
    "msl": ["us_nga_egm96_15.tif", "egm96_15.gtx"],
    # N60 has no single-step HAE grid in the PROJ CDN; users must supply --geoid-grid.
    "n60": [],
    "hae": [],
}

#: Vertical EPSG codes mapped to input datum. Compound CRSs containing any of
#: these codes resolve to the same datum.
_EPSG_TO_DATUM = {
    3900: "n2000",  # N2000 height
    3901: "n60",  # KKJ + N60 height (compound)
    3902: "n60",  # ETRS89 / TM35FIN + N60 height (compound)
    3903: "n2000",  # ETRS89 / TM35FIN + N2000 height (compound)
    5717: "n60",  # N60 height
    5773: "msl",  # EGM96 height
    5798: "msl",  # EGM84 height
    3855: "msl",  # EGM2008 height
    4979: "hae",  # WGS 84 3D (ellipsoidal)
    4937: "hae",  # ETRS89 3D (ellipsoidal)
    7912: "hae",  # EUREF-FIN 3D (ellipsoidal)
}

# Human-readable hints for missing-grid errors.
_GRID_HINTS = {
    "n2000": (
        "Finnish N2000 -> HAE requires a geoid undulation grid (FIN2023N2000, "
        "fi_nls_fin2023n2000.tif or fi_nls_fin2005n00.tif). The tool auto-downloads "
        "it from https://cdn.proj.org/ unless --no-geoid-download is given; "
        "alternatively pass it via --geoid-grid or use a constant --vertical-offset "
        "(less accurate, undulation varies ~15-25 m across Finland)."
    ),
    "n60": (
        "Finnish N60 -> HAE requires a geoid undulation grid. "
        "Pass it via --geoid-grid or use a constant --vertical-offset."
    ),
    "msl": (
        "MSL -> HAE requires a geoid undulation grid (e.g. EGM96 us_nga_egm96_15.tif). "
        "The tool auto-downloads it from https://cdn.proj.org/ unless "
        "--no-geoid-download is given; alternatively pass it via --geoid-grid "
        "or use --vertical-offset."
    ),
}


@dataclass(frozen=True)
class VerticalShift:
    """Describes how to shift DEM values from input datum to output datum."""

    input_datum: str
    output_datum: str  # "hae" or "msl"
    direction: int  # +1: H = H + N (to HAE), -1: h = h - N (to MSL), 0: no shift
    needs_grid: bool


def resolve_shift(input_datum: str, output_datum: str) -> VerticalShift:
    """Resolve conversion direction between input and output datum."""
    inp = input_datum.lower()
    out = output_datum.lower()
    if inp not in INPUT_DATUMS:
        raise ValueError(f"Unknown input datum {input_datum!r}, expected one of {INPUT_DATUMS}")
    if out not in OUTPUT_DATUMS:
        raise ValueError(f"Unknown output datum {output_datum!r}, expected one of {OUTPUT_DATUMS}")

    if inp == "hae" and out == "hae":
        return VerticalShift(inp, out, 0, False)
    if inp == "msl" and out == "msl":
        # Treat generic MSL as identity; N2000/N60 vs MSL differences are not modelled here.
        return VerticalShift(inp, out, 0, False)
    if inp in ("n2000", "n60") and out == "msl":
        # Both are gravity-related; without an explicit N2000<->MSL model we treat
        # them as identical rather than failing. Documented approximation.
        return VerticalShift(inp, out, 0, False)
    if out == "hae" and inp in ("msl", "n2000", "n60"):
        return VerticalShift(inp, out, +1, True)
    if inp == "hae" and out == "msl":
        return VerticalShift(inp, out, -1, True)
    # Fallback (should be unreachable given the cases above).
    return VerticalShift(inp, out, 0, False)


def validate_shift_inputs(
    shift: VerticalShift,
    geoid_grid: Optional[str],
    vertical_offset: Optional[float],
) -> None:
    """Raise a helpful error if a required grid/offset is missing."""
    if not shift.needs_grid:
        return
    if geoid_grid is None and vertical_offset is None:
        hint = _GRID_HINTS.get(shift.input_datum if shift.direction == 1 else "msl", "")
        if shift.direction == -1:
            hint = (
                "HAE -> MSL requires a geoid undulation grid. "
                "Pass it via --geoid-grid or use a constant --vertical-offset."
            )
        raise ValueError(
            f"Converting input datum {shift.input_datum!r} to {shift.output_datum!r} "
            f"requires --geoid-grid or --vertical-offset. {hint}"
        )


def open_geoid_dataset(geoid_path: str) -> gdal.Dataset:
    """Open a geoid undulation grid (GeoTIFF with N in metres, h = H + N)."""
    ds = gdal.Open(geoid_path)
    if ds is None:
        raise ValueError(f"Unable to open --geoid-grid {geoid_path!r}")
    return ds


def detect_datum_from_wkt(wkt: str) -> Optional[str]:
    """Detect the vertical datum from a CRS WKT string via EPSG authority codes."""
    if not wkt:
        return None
    codes = re.findall(r'ID\["EPSG",\s*"?(\d+)"?\]', wkt)
    codes += re.findall(r'AUTHORITY\["EPSG",\s*"?(\d+)"?\]', wkt)
    found: List[str] = []
    for code in codes:
        datum = _EPSG_TO_DATUM.get(int(code))
        if datum is not None and datum not in found:
            found.append(datum)
    # Priority: gravity-related systems first (they carry the signal), then hae.
    for datum in ("n2000", "n60", "msl", "hae"):
        if datum in found:
            return datum
    return None


def detect_datum_from_path(path: str) -> Optional[str]:
    """Detect datum from file/directory naming hints (fallback for 2D CRSs).

    Finnish MML DEMs, for example, carry a pure 2D EPSG:3067 CRS in the file
    while the distribution path states the height system (etrs-tm35fin-n2000).
    """
    name = path.lower()
    if "n2000" in name or "fin2005" in name or "fin2023" in name:
        return "n2000"
    if re.search(r"(?<![a-z0-9])n60(?![a-z0-9])", name):
        return "n60"
    if "egm96" in name or "egm2008" in name or "egm84" in name or "evrs" in name:
        return "msl"
    if re.search(r"(?<![a-z0-9])msl(?![a-z0-9])", name) or "orthometric" in name:
        return "msl"
    if re.search(r"(?<![a-z0-9])hae(?![a-z0-9])", name) or "ellipsoid" in name:
        return "hae"
    return None


def _list_input_files(input_path: str, sample_limit: int = 20) -> List[str]:
    if os.path.isdir(input_path):
        files = sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith((".tif", ".tiff"))
        )
        return files[:sample_limit]
    return [input_path]


def detect_input_datum(input_path: str, sample_limit: int = 20) -> Tuple[str, str]:
    """Auto-detect the input vertical datum.

    Strategy (no hardcoding of a single survey):
      1. Inspect the embedded CRS of up to ``sample_limit`` files. A compound
         or vertical CRS (e.g. EPSG:3900 N2000, EPSG:5773 EGM96, EPSG:4979 3D)
         is strong evidence.
      2. Fall back to file/directory naming hints (e.g. ``etrs-tm35fin-n2000``).
      3. Default to ``hae`` (historic behaviour: no conversion).

    Returns (datum, evidence-string for logging).
    """
    files = _list_input_files(input_path, sample_limit)
    if not files:
        raise ValueError("No input files found.")

    votes: Dict[str, int] = {}
    for path in files:
        try:
            ds = gdal.Open(path)
            if ds is None:
                continue
            datum = detect_datum_from_wkt(ds.GetProjection() or "")
            if datum is not None:
                votes[datum] = votes.get(datum, 0) + 1
        except RuntimeError:
            continue
        except ValueError:
            continue

    if votes:
        best = max(votes, key=lambda k: votes[k])
        return best, (f"embedded CRS vertical datum in {votes[best]}/{len(files)} sampled file(s)")

    # No vertical CRS embedded (e.g. MML 2m DEM is plain EPSG:3067) -> naming hints.
    hint_sources = [input_path] + files[:5]
    for source in hint_sources:
        datum = detect_datum_from_path(source)
        if datum is not None:
            return datum, f"naming hint in {source!r}"

    return "hae", "no vertical CRS or naming hint found; assuming hae (no conversion)"


def get_cache_dir() -> str:
    """Directory for auto-downloaded geoid grids."""
    cache = os.path.join(os.path.expanduser("~"), ".cache", "geotiff-to-tak-terrain", "grids")
    os.makedirs(cache, exist_ok=True)
    return cache


def _candidate_search_dirs() -> List[str]:
    dirs: List[str] = []
    for env in ("PROJ_DATA", "PROJ_LIB"):
        val = os.environ.get(env)
        if val:
            dirs.extend(val.split(os.pathsep))
    dirs += ["/usr/share/proj", "/usr/local/share/proj", "/opt/homebrew/share/proj"]
    return [d for d in dirs if d and os.path.isdir(d)]


def _download_grid(filename: str, dest_dir: str) -> Optional[str]:
    dest = os.path.join(dest_dir, filename)
    if os.path.exists(dest):
        return dest
    url = f"{PROJ_CDN_ENDPOINT}/{filename}"
    try:
        logger.info("Downloading geoid grid %s ...", url)
        urllib.request.urlretrieve(url, dest)
        return dest
    except (OSError, ValueError) as exc:  # pragma: no cover - network dependent
        logger.warning("Could not download %s: %s", url, exc)
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except OSError:
            pass
        return None


def resolve_geoid_grid(
    input_datum: str,
    user_grid: Optional[str] = None,
    allow_download: bool = True,
    cache_dir: Optional[str] = None,
) -> Optional[str]:
    """Resolve the geoid grid file for ``input_datum`` -> HAE without hardcoding one survey.

    Order: explicit ``--geoid-grid`` > locally installed PROJ grids > cached
    downloads > fresh download from the PROJ CDN. Returns None when no
    automatic grid exists (e.g. N60) or nothing was found.
    """
    if user_grid:
        if not os.path.exists(user_grid):
            raise ValueError(f"--geoid-grid not found: {user_grid!r}")
        return user_grid

    candidates = GEOID_GRID_CANDIDATES.get(input_datum.lower(), [])
    if not candidates:
        return None

    search_dirs = _candidate_search_dirs()
    if cache_dir is None:
        try:
            cache_dir = get_cache_dir()
        except OSError:
            cache_dir = None
    if cache_dir:
        search_dirs.append(cache_dir)

    for filename in candidates:
        for directory in search_dirs:
            candidate = os.path.join(directory, filename)
            if os.path.exists(candidate):
                return candidate

    if allow_download and cache_dir:
        # Only attempt the preferred (first) candidate for download.
        downloaded = _download_grid(candidates[0], cache_dir)
        if downloaded:
            return downloaded

    return None


def sample_geoid(
    geoid_ds: gdal.Dataset,
    bounds: Tuple[float, float, float, float],
    width: int,
    height: int,
) -> Optional[NDArray[np.float32]]:
    """Sample geoid undulation N over bounds (min_lon, min_lat, max_lon, max_lat).

    Returns a float32 array of shape (height, width) or None if the grid does
    not cover the tile at all.
    """
    try:
        out_ds = gdal.Warp(
            "",
            geoid_ds,
            format="MEM",
            outputBounds=[bounds[0], bounds[1], bounds[2], bounds[3]],
            width=width,
            height=height,
            dstSRS="EPSG:4326",
            srcSRS="EPSG:4326",
            resampleAlg=gdal.GRA_Bilinear,
        )
    except RuntimeError:
        return None
    if out_ds is None:
        return None
    band = out_ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    if arr is None:
        return None
    nodata = band.GetNoDataValue()
    arr = np.asarray(arr, dtype=np.float32)
    if nodata is not None and np.isfinite(nodata):
        invalid = arr == np.float32(nodata)
        if np.all(invalid):
            return None
        # Mark gaps as NaN so the caller can fall back per-pixel.
        arr = arr.astype(np.float32)
        arr[invalid] = np.nan
    if np.all(~np.isfinite(arr)):
        return None
    return arr


def apply_vertical_shift(
    data: NDArray[np.float32],
    valid_mask: NDArray[np.bool_],
    shift: VerticalShift,
    geoid_n: Optional[NDArray[np.float32]] = None,
    vertical_offset: Optional[float] = None,
) -> NDArray[np.float32]:
    """Apply datum shift in-place on a copy and return the shifted array.

    Only pixels where valid_mask is True are shifted. If a geoid grid is given,
    per-pixel undulation is used where finite; pixels with NaN undulation fall
    back to vertical_offset (if given) or are left unshifted.
    """
    if shift.direction == 0:
        return data
    out = data.astype(np.float32, copy=True)
    if geoid_n is not None:
        finite = np.isfinite(geoid_n) & valid_mask
        if shift.direction == 1:
            out[finite] = data[finite] + geoid_n[finite]
        else:
            out[finite] = data[finite] - geoid_n[finite]
        remaining = valid_mask & ~np.isfinite(geoid_n)
        if vertical_offset is not None and np.any(remaining):
            if shift.direction == 1:
                out[remaining] = data[remaining] + np.float32(vertical_offset)
            else:
                out[remaining] = data[remaining] - np.float32(vertical_offset)
    elif vertical_offset is not None:
        if shift.direction == 1:
            out[valid_mask] = data[valid_mask] + np.float32(vertical_offset)
        else:
            out[valid_mask] = data[valid_mask] - np.float32(vertical_offset)
    return out
