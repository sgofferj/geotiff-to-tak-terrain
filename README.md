# GeoTIFF to TAK LCLL Terrain Converter

> [!WARNING]
> Versions before vertical-datum support wrote input elevations straight into the tiles and only
> set the `heights` metadata flag — the vertical datum was **never converted**. ATAK expects
> heights above the ellipsoid (HAE), so tiles generated from orthometric/normal-height DEMs
> (e.g. Finnish MML data in N2000) are off by the local geoid undulation (about **−19 m at sea
> level around Helsinki**). If your source DEM is not already HAE, **regenerate your tiles**
> with a version that includes the `--input-datum` fix (input datum is now auto-detected and
> converted to HAE via the matching geoid grid).

Convert Digital Elevation Model (DEM) GeoTIFFs into the **LCLL (Low Complexity Low Latency)** terrain format used by TAK (ATAK, WinTAK).

## Format Details
- **Tiling Scheme**: EPSG:4326 (Geographic) Slippy/Google (Root Level 0 = 2 tiles).
- **Encoding**: Mapbox Terrain-RGB (8-bit RGBA PNG).
- **Metadata**: Embedded `tAKa` PNG chunk containing tile indices and coordinate system info.

## Usage (Docker)

### Build
```bash
docker build -t geotiff-to-tak-terrain .
```

### Run
```bash
docker run --rm
  -v /path/to/geotiffs:/data/in:ro
  -v /path/to/output:/data/out
  geotiff-to-tak-terrain
  /data/in /data/out --title "My Custom Terrain"
```

## Local Development (Poetry)

### Installation
```bash
poetry install
```

### Quality Checks
```bash
poetry run black .
poetry run mypy .
poetry run pylint src/geotiff_to_tak_terrain
```

### Execution
```bash
poetry run geotiff-to-tak-terrain <input_path> <output_dir> [options]
```

## Documentation
- [Why do the tiles look so weird?](psychedelic.md) - Understanding Terrain-RGB encoding.
- [Performance Example: Finland MML](example_stats.md) - Real-world benchmarks and hardware recommendations.
- [How to serve tiles](How_to_serve_tiles.md) - Guide for setting up a web server for ATAK.

## Parameters
- `input`: Path to a GeoTIFF file or a directory containing multiple files.
- `output`: Directory where tiles and `config.json` will be saved.
- `--title`: Title of the map source in ATAK.
- `--min-zoom`: Minimum zoom level (default: 0).
- `--max-zoom`: Maximum zoom level (default: 14).
- `--data-source`: Data source name for metadata (default: Local DEM).
- `--heights`: Output height datum, either `hae` (default, as ATAK expects HAE) or `msl`.
- `--input-datum`: Vertical datum of the input DEM: `auto` (default), `hae`, `msl`, `n2000`, `n60`.
  `auto` detects the datum from the embedded CRS (e.g. EPSG:3900 for N2000, EPSG:5773 for EGM96,
  EPSG:4979 for ellipsoidal) or from naming hints such as `etrs-tm35fin-n2000`
  (Finnish MML 2 m DEM carries a plain 2D EPSG:3067 CRS, so the path name is the evidence),
  and falls back to `hae` (no conversion).
- `--geoid-grid`: Geoid undulation grid (GeoTIFF, N in metres, h = H + N). If omitted, the matching
  grid is auto-selected: FIN2023N2000 (`fi_nls_fin2023n2000.tif`) for N2000, EGM96 for MSL —
  searched in local PROJ data dirs and `~/.cache/geotiff-to-tak-terrain/grids/`,
  otherwise downloaded from `https://cdn.proj.org/`.
- `--no-geoid-download`: Disable automatic geoid grid download.
- `--vertical-offset`: Constant offset in metres (h = H + offset), used where the grid has no
  coverage. Less accurate than a grid (undulation varies ~15–25 m across Finland).
- `--workers`: Number of parallel worker processes (default: `min(8, CPU_COUNT // 2)`).

### Vertical datum examples
```bash
# Finnish MML 2 m DEM (N2000) -> HAE for ATAK (auto-detects n2000, downloads FIN2023N2000 grid)
/data/in /data/out --title "Finland MML"

# Explicit input datum with your own grid
/data/in /data/out --input-datum n2000 --geoid-grid /data/grids/fi_nls_fin2023n2000.tif

# Crude constant shift (only if you know the local undulation)
/data/in /data/out --input-datum n2000 --vertical-offset 19.0
```

## Memory Usage and Performance
Memory consumption varies significantly based on the zoom level and the number of workers:

- **Zoom 0-5 (High Memory):** At low zoom levels, each tile covers a large geographic area. Each worker must scan and downsample from many (potentially all) input GeoTIFF files simultaneously. This causes peak memory usage (e.g., ~10GB for 8 workers with 1,500+ source files).
- **Zoom 6-14 (Low Memory):** At higher zoom levels, each tile covers a very small area, often touching only 1 or 2 source files. Memory usage drops and stabilizes (e.g., ~4.5GB for 8 workers).
- **Parallelism:** The tool defaults to a conservative number of workers to prevent Out-Of-Memory (OOM) crashes. For a system with 16GB RAM, **8 workers** is typically the "sweet spot" for performance and stability.

**Pro-tip:** To dramatically speed up low-zoom tile generation, pre-generate internal overviews for your source TIFFs using `gdaladdo -r average *.tif`.

## License
Copyright (c) 2026 Stefan Gofferje <stefan@gofferje.net>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
