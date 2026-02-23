# GeoTIFF to TAK LCLL Terrain Converter

Convert Digital Elevation Model (DEM) GeoTIFFs into the **LCLL (Low Complexity Low Latency)** terrain format used by TAK (ATAK, WinTAK, CloudTAK).

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
- `--heights`: Height datum, either `hae` (default) or `msl`.
- `--workers`: Number of parallel worker processes (default: `min(8, CPU_COUNT // 2)`).

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
