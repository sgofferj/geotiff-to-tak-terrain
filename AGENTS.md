# Project Context: geotiff-to-tak-terrain

## Technical Overview
- **Objective:** Convert GeoTIFF DEMs into TAK-compatible LCLL Terrain-RGB tiles.
- **Entry Point:** `src/geotiff_to_tak_terrain/main.py`.
- **Core Stack:** GDAL (Warping/VRT), NumPy (Data processing), PyPNG (RGBA encoding + custom metadata chunks).
- **Vertical Datum Module:** `src/geotiff_to_tak_terrain/datum.py` (detection, geoid grids, shift math).

## Vertical Datum Handling (ATAK expects HAE)
- **Rule:** Output defaults to HAE (`--heights hae`). Input datum is auto-detected (`--input-datum auto`):
  embedded CRS first (EPSG:3900 N2000, 5717 N60, 5773/3855 MSL, 4979 3D HAE, incl. compounds like 3903),
  then filename/path hints (e.g. `etrs-tm35fin-n2000` — MML DEMs carry a plain 2D EPSG:3067 CRS),
  fallback `hae` (no conversion, historic behaviour).
- **Conversion:** `h = H + N`, per-tile bilinear sampling of the geoid grid (256×256, EPSG:4326),
  valid-pixels only; `--vertical-offset` is the fallback where the grid has no coverage.
- **Grid registry (nothing hardcoded to one survey):** N2000 → FIN2023N2000 (`fi_nls_fin2023n2000.tif`,
  fallback FIN2005N00); MSL → EGM96 (`us_nga_egm96_15.tif`, local `egm96_15.gtx`); N60 has no
  auto grid (user must supply `--geoid-grid`). Resolution order: `--geoid-grid` > local PROJ
  data dirs > `~/.cache/geotiff-to-tak-terrain/grids/` > download from `https://cdn.proj.org/`
  (`--no-geoid-download` disables fetching).
- **History:** Versions before this feature never converted elevations (only set the `heights`
  metadata flag). Tiles built from non-HAE DEMs are off by the local undulation — e.g. ≈ −19 m
  at sea level around Helsinki for N2000 input — and must be regenerated. README carries a
  `[!WARNING]` callout about this.

## Parallelism & Stability
- **Execution:** Uses `multiprocessing.Pool` for speed.
- **Worker Configuration:**
    - **Default Count:** `min(8, CPU_COUNT // 2)` (optimized for 16GB RAM systems).
    - **Chunksize:** Always use `chunksize=1` in `imap_unordered` to ensure granular task distribution for heavy DEM tasks.
    - **Memory Safety:** `maxtasksperchild=50` is mandatory to clear GDAL caches and prevent memory accumulation.
    - Each worker opens the source VRT plus the resolved geoid grid (`worker_init`).
- **Memory Profile:** Expect ~10GB system RAM usage at Zoom 0-5 (due to massive file scanning) and ~4.5GB at Zoom 6+ (optimized single-file access).

## Architectural Requirements
- **Root Tiles:** Zoom 0 tiles (0/0/0 and 0/1/0) must **always** be generated, even if they are empty (transparent).
- **PNG Encoding:** The RGBA array must be reshaped to `(256, -1)` before passing to `pypng.Writer.write()` to ensure correct interleaved values.
- **Metadata:** Custom JSON metadata is stored in a `tAKa` chunk injected before the `IEND` marker.
- **Config:** `generate_config` derives bounds from rendered tiles, skipping Zoom 0 (world-covering).

## Local Environment
- **Dataset Location (MML 10m):** `/media/sgofferj/3F26D5F050FDC36C/Cesium/10m TIFF` (N2000 normal heights).
- **Output Resolution:** ~15m/pixel at Zoom 14.
- **GDAL Pin:** `pyproject.toml` pins `gdal` to the system libgdal version (currently 3.11.4).
  The Python bindings must match libgdal minor — a mismatch breaks `ReadAsArray` (`_gdal_array`
  import error). After OS GDAL upgrades, bump the pin and run `poetry lock && poetry install`.
  Docker builds install their own GDAL via apt; keep the pin in sync with the image's libgdal.

## Session Wrap-up (2026-02-28 - Morning)
- **Status:** Optimization work is complete and verified stable.
- **Key Milestones:**
    - **Compression:** Integrated `feature/atak-config-compression` into the main line, allowing for more compact metadata handling.
    - **Verification:** Long-running stability test (started Thursday) passed without crashes or artifacts.
    - **Git:** Merged `optimizing` (including compression features) into `main` and deleted the local/remote feature and optimization branches.
- **Final Result:** The tool is now highly resilient, supports resumable processing (`--skip-existing`), and efficiently handles millions of tiles with low memory overhead.
- **GitHub:** `main` is now up-to-date with all the latest architectural improvements.

## Session Wrap-up (2026-09-26)
- **Vertical datum fix:** MML input verified as N2000 (2D EPSG:3067 + `etrs-tm35fin-n2000` path evidence;
  FIN2023N2000 undulation ≈ 19 m at the M4111 test tile). Added `datum.py`, `--input-datum`/`--geoid-grid`/
  `--no-geoid-download`/`--vertical-offset` CLI, auto-detection + auto grid download. End-to-end check:
  100 m N2000 → ≈ 118.9 m HAE in output tile. Field symptom this fixes: −19 m at sea level near Helsinki.
- **Venv:** Refreshed to GDAL bindings 3.11.4 matching system libgdal (fixes `_gdal_array` breakage).
- **Docs:** Renamed `GEMINI.md` → `AGENTS.md` (now tracked; removed from `.gitignore`), README warning
  callout added, datum parameters documented.
