#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tyler.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

import math
from typing import Tuple, Iterator


def get_tile_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """
    Calculate geographic bounds of a tile in EPSG:4326 (Slippy/Google scheme).
    Level 0: 2 tiles (West/East).
    X range: 0 to (2^(z+1) - 1)
    Y range: 0 to (2^z - 1)
    """
    tiles_x = 2 ** (z + 1)
    tiles_y = 2**z

    lon_width = 360.0 / tiles_x
    lat_height = 180.0 / tiles_y

    min_lon = -180.0 + x * lon_width
    max_lon = min_lon + lon_width

    # Y=0 is North Pole (90), Y increases Southward
    max_lat = 90.0 - y * lat_height
    min_lat = max_lat - lat_height

    return min_lon, min_lat, max_lon, max_lat


def get_intersecting_tiles(
    extent: Tuple[float, float, float, float], z: int
) -> Iterator[Tuple[int, int]]:
    """
    Yield x, y for tiles that intersect the given extent (min_lon, min_lat, max_lon, max_lat)
    at zoom level z.
    """
    tiles_x = 2 ** (z + 1)
    tiles_y = 2**z

    lon_width = 360.0 / tiles_x
    lat_height = 180.0 / tiles_y

    start_x = int(math.floor((extent[0] + 180.0) / lon_width))
    end_x = int(math.floor((extent[2] + 180.0) / lon_width))

    # Y increases southward
    start_y = int(math.floor((90.0 - extent[3]) / lat_height))
    end_y = int(math.floor((90.0 - extent[1]) / lat_height))

    # Clamp to world limits
    start_x = max(0, start_x)
    end_x = min(tiles_x - 1, end_x)
    start_y = max(0, start_y)
    end_y = min(tiles_y - 1, end_y)

    for ty in range(start_y, end_y + 1):
        for tx in range(start_x, end_x + 1):
            yield tx, ty
