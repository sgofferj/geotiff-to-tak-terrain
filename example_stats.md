# Performance Example: Finland MML 10m DEM

This document provides a real-world performance benchmark for converting a large-scale regional DEM dataset into TAK-compatible LCLL terrain tiles.

## Dataset Overview
- **Source Material:** Maanmittauslaitos (MML) 10m Elevation Model.
- **Input Format:** 1,524 GeoTIFF files (Float32, approx. 17GB raw).
- **Extent:** Southern to Northern Finland (approx. 15° to 33° E, 59° to 70° N).
- **Zoom Levels:** 0 to 14.
- **Output Resolution:** ~15m/pixel at Zoom 14.

## Hardware & Configuration
- **CPU:** 16 Cores (AMD/Intel).
- **RAM:** 16GB.
- **Workers:** 8 parallel processes (configured to `min(8, CPU_COUNT // 2)`).
- **Memory Safety:** `maxtasksperchild=50` (to prevent GDAL memory creep).
- **Storage:** Network Attached Storage (NAS) via 1GbE/10GbE.

## Conversion Statistics
- **Total Tiles Generated:** 798,589
- **Total Duration:** 7 hours, 29 minutes
- **Average Performance:** ~30 tiles per second (overall average).

### Timing Breakdown by Zoom Level
| Zoom Level | Tile Count | Duration | Profile |
| :--- | :--- | :--- | :--- |
| **0 - 2** | 4 | ~30 mins | **Bottleneck:** Heavy downsampling from 1,500+ TIFFs without overviews. |
| **3 - 9** | 948 | ~15 mins | **Transition:** Workers begin hitting fewer files per tile. |
| **10 - 11** | 12,171 | ~7 mins | **Peak Speed:** Perfectly balanced CPU/IO workload. |
| **12** | 37,939 | 20 mins | **Scaling:** Parallel processing fully utilized. |
| **13** | 150,146 | 1h 20m | **Volume:** Heavy PNG encoding load. |
| **14** | 597,374 | 4h 57m | **IO Bound:** Limited by NAS file-write latency. |

## Observations
- **Memory Efficiency:** System RAM usage peaked at 10GB during low-zoom "heavy scans" and dropped to a stable 4.5GB during high-zoom production.
- **Stability:** The `maxtasksperchild` setting resulted in over 15,000 clean worker process lifecycles, ensuring zero memory accumulation over the 7-hour run.
- **Storage Impact:** Generating over half a million small files in the final zoom level is extremely demanding on file system IOPS; a high-speed SSD or optimized NAS is recommended for Zoom 14+ runs.
