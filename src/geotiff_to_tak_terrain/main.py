#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

import os
import json
import logging
import argparse
import io
from typing import Tuple, Dict
import numpy as np
from osgeo import gdal
import png  # pypng for custom chunk support

from .tyler import get_tile_bounds, get_intersecting_tiles
from .encoder import encode_terrain_rgb
from .metadata import create_taka_chunk

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

gdal.UseExceptions()

TILE_SIZE = 256


def process_tile(
    ds: gdal.Dataset,
    tile_coord: Tuple[int, int, int],
    dest_dir: str,
    meta_params: Dict[str, str],
) -> bool:
    """Extract DEM data, encode as Terrain-RGB PNG, and add tAKa chunk."""
    z, tx, ty = tile_coord
    bounds = get_tile_bounds(z, tx, ty)
    tile_dir = os.path.join(dest_dir, str(z), str(tx))
    tile_path = os.path.join(tile_dir, f"{ty}.png")

    try:
        # Warp to tile extent
        out_ds = gdal.Warp(
            "",
            ds,
            format="MEM",
            outputBounds=[bounds[0], bounds[1], bounds[2], bounds[3]],
            width=TILE_SIZE,
            height=TILE_SIZE,
            dstSRS="EPSG:4326",
            resampleAlg=gdal.GRA_Bilinear,
        )

        data = out_ds.ReadAsArray()
        if data is None:
            return False

        # Check if tile has data
        band = out_ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        if nodata is None:
            nodata = -9999

        mask = (data > nodata).astype(np.uint8) * 255
        if np.max(mask) == 0:
            return False

        # Encode RGB
        rgb = encode_terrain_rgb(data)
        rgba = np.dstack((rgb, mask))
        rgba_flat = rgba.reshape(TILE_SIZE, TILE_SIZE * 4)

        # Prepare metadata chunk
        metadata = {
            "tileIndex": {"x": tx, "y": ty, "z": z},
            "heights": meta_params["heights_type"],
            "dataSource": meta_params["data_source"],
            "srid": 4326,
        }
        taka_chunk = create_taka_chunk(metadata)

        # Save using pypng to inject chunk
        os.makedirs(tile_dir, exist_ok=True)
        with open(tile_path, "wb") as f:
            w = png.Writer(width=TILE_SIZE, height=TILE_SIZE, alpha=True, bitdepth=8)
            buf = io.BytesIO()
            w.write(buf, rgba_flat)
            png_data = buf.getvalue()

            # Inject tAKa chunk before IEND
            iend_pos = png_data.find(b"IEND")
            if iend_pos != -1:
                new_png_data = png_data[: iend_pos - 4] + taka_chunk + png_data[iend_pos - 4 :]
                f.write(new_png_data)
            else:
                f.write(png_data)

        return True
    except (RuntimeError, ValueError, io.UnsupportedOperation) as e:
        logger.debug("Failed to process tile %d/%d/%d: %s", z, tx, ty, e)
        return False


def get_input_dataset(input_path: str) -> Tuple[gdal.Dataset, Tuple[float, float, float, float]]:
    """Open input GeoTIFF(s) and return the dataset and its geographic extent."""
    if os.path.isdir(input_path):
        files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith((".tif", ".tiff"))
        ]
    else:
        files = [input_path]

    if not files:
        raise ValueError("No input files found.")

    logger.info("Found %d files. Opening...", len(files))

    # Use VRT to merge multiple files if necessary
    vrt_path = "/tmp/input.vrt"
    gdal.BuildVRT(vrt_path, files)
    ds = gdal.Open(vrt_path)

    # Get extent in EPSG:4326
    warp_vrt = "/tmp/extent.vrt"
    gdal.Warp(warp_vrt, ds, format="VRT", dstSRS="EPSG:4326")
    wds = gdal.Open(warp_vrt)
    gt = wds.GetGeoTransform()

    # gt: (ulx, xres, xskew, uly, yskew, yres)
    extent = (gt[0], gt[3] + wds.RasterYSize * gt[5], gt[0] + wds.RasterXSize * gt[1], gt[3])
    return wds, extent


def generate_config(
    output_dir: str, title: str, max_zoom: int, data_source: str, heights: str
) -> None:
    """Generate the config.json for ATAK Map Source."""
    config = {
        "schema": "2.1.0",
        "title": title,
        "content": "terrain",
        "mimeType": "application/vnd.mapbox-terrain-rgb",
        "downloadable": True,
        "refreshInterval": 0,
        "isQuadtree": True,
        "url": "{z}/{x}/{y}.png",
        "srs": "EPSG:4326",
        "numLevels": max_zoom + 1,
        "tileMatrix": [
            {
                "level": 0,
                "pixelSizeX": 0.703125,
                "pixelSizeY": 0.703125,
                "tileWidth": 256,
                "tileHeight": 256,
                "resolution": 156543.034,
            }
        ],
        "metadata": {"heights": heights, "dataSource": data_source},
    }
    with open(os.path.join(output_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoTIFF to TAK LCLL Terrain Tiles")
    parser.add_argument("input", help="Input GeoTIFF or directory")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--title", default="TAK Terrain", help="Layer title")
    parser.add_argument("--min-zoom", type=int, default=0, help="Min zoom level")
    parser.add_argument("--max-zoom", type=int, default=14, help="Max zoom level")
    parser.add_argument("--data-source", default="Local DEM", help="Data source name")
    parser.add_argument("--heights", choices=["hae", "msl"], default="hae", help="Height datum")

    args = parser.parse_args()

    heights_type = "ellipsoidal" if args.heights == "hae" else "orthometric"

    try:
        ds, extent = get_input_dataset(args.input)
        logger.info("Dataset extent (WGS84): %s", extent)

        meta_params = {"heights_type": heights_type, "data_source": args.data_source}

        for z in range(args.min_zoom, args.max_zoom + 1):
            count = 0
            for tx, ty in get_intersecting_tiles(extent, z):
                if process_tile(ds, (z, tx, ty), args.output, meta_params):
                    count += 1
            if count > 0:
                logger.info("Level %d: Generated %d tiles", z, count)

        generate_config(args.output, args.title, args.max_zoom, args.data_source, args.heights)
        logger.info("Done!")

    except (RuntimeError, ValueError) as e:
        logger.error("Error: %s", e)


if __name__ == "__main__":
    main()
