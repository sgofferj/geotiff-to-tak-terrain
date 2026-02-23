# Project Context: geotiff-to-tak-terrain

## Technical Overview
- **Objective:** Convert GeoTIFF DEMs into TAK-compatible LCLL Terrain-RGB tiles.
- **Entry Point:** `src/geotiff_to_tak_terrain/main.py`.
- **Core Stack:** GDAL (Warping/VRT), NumPy (Data processing), PyPNG (RGBA encoding + custom metadata chunks).

## Parallelism & Stability
- **Execution:** Uses `multiprocessing.Pool` for speed.
- **Worker Configuration:**
    - **Default Count:** `min(8, CPU_COUNT // 2)` (optimized for 16GB RAM systems).
    - **Chunksize:** Always use `chunksize=1` in `imap_unordered` to ensure granular task distribution for heavy DEM tasks.
    - **Memory Safety:** `maxtasksperchild=50` is mandatory to clear GDAL caches and prevent memory accumulation.
- **Memory Profile:** Expect ~10GB system RAM usage at Zoom 0-5 (due to massive file scanning) and ~4.5GB at Zoom 6+ (optimized single-file access).

## Architectural Requirements
- **Root Tiles:** Zoom 0 tiles (0/0/0 and 0/1/0) must **always** be generated, even if they are empty (transparent).
- **PNG Encoding:** The RGBA array must be reshaped to `(256, -1)` before passing to `pypng.Writer.write()` to ensure correct interleaved values.
- **Metadata:** Custom JSON metadata is stored in a `tAKa` chunk injected before the `IEND` marker.

## Local Environment
- **Dataset Location (MML 10m):** `/media/sgofferj/3F26D5F050FDC36C/Cesium/10m TIFF`
- **Output Resolution:** ~15m/pixel at Zoom 14.
