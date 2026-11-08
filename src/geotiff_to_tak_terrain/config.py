#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# config.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

"""Creation of the TAK streaming-tiles config.json (LCLL terrain)."""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .tyler import get_tile_bounds


@dataclass
class ConfigParams:
    """Parameters for generate_config."""

    output_dir: str
    title: str
    data_source: str
    heights: str
    max_z: Optional[int] = None
    extent: Optional[Tuple[float, float, float, float]] = None


def get_rendered_metadata(
    output_dir: str,
) -> Tuple[int, Optional[Tuple[float, float, float, float]]]:
    """Discover max zoom and geographic extent from rendered tiles on disk."""
    max_z = -1
    overall_extent: Optional[List[float]] = None

    if not os.path.exists(output_dir):
        return max_z, None

    for z_str in os.listdir(output_dir):
        if not z_str.isdigit():
            continue
        z = int(z_str)
        max_z = max(max_z, z)

        # Skip Zoom 0 for extent calculation as it always covers the whole world
        if z == 0:
            continue

        z_dir = os.path.join(output_dir, z_str)
        for x_str in os.listdir(z_dir):
            if not x_str.isdigit():
                continue
            tx = int(x_str)
            x_dir = os.path.join(z_dir, x_str)
            for y_file in os.listdir(x_dir):
                if not y_file.endswith(".png"):
                    continue
                try:
                    ty = int(y_file.split(".")[0])
                    bounds = get_tile_bounds(z, tx, ty)
                    if overall_extent is None:
                        overall_extent = [bounds[0], bounds[1], bounds[2], bounds[3]]
                    else:
                        overall_extent[0] = min(overall_extent[0], bounds[0])
                        overall_extent[1] = min(overall_extent[1], bounds[1])
                        overall_extent[2] = max(overall_extent[2], bounds[2])
                        overall_extent[3] = max(overall_extent[3], bounds[3])
                except ValueError:
                    continue

    if overall_extent:
        return max_z, (
            overall_extent[0],
            overall_extent[1],
            overall_extent[2],
            overall_extent[3],
        )
    return max_z, None


def generate_config(params: ConfigParams) -> None:
    """Generate the config.json for ATAK Map Source."""
    max_z = params.max_z
    extent = params.extent

    if max_z is None or extent is None:
        metadata_max_z, metadata_extent = get_rendered_metadata(params.output_dir)
        if max_z is None:
            max_z = metadata_max_z
        if extent is None:
            extent = metadata_extent

    config: Dict[str, Any] = {
        "schema": "2.1.0",
        "title": params.title,
        "content": "terrain",
        "mimeType": "application/vnd.mapbox-terrain-rgb",
        "downloadable": True,
        "refreshInterval": 0,
        "isQuadtree": True,
        "url": "{$z}/{$x}/{$y}.png",
        "srs": "EPSG:4326",
        "numLevels": max_z + 1,
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
        "metadata": {"heights": params.heights, "dataSource": params.data_source},
    }

    if extent is not None:
        # extent: (min_lon, min_lat, max_lon, max_lat)
        # TAK's StreamingTiles parser requires minX/minY/maxX/maxY; using
        # minLon/minLat/... makes the whole config parse fail silently.
        config["bounds"] = {
            "minX": extent[0],
            "minY": extent[1],
            "maxX": extent[2],
            "maxY": extent[3],
        }

    with open(os.path.join(params.output_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
