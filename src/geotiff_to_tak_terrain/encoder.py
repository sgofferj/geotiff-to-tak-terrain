#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# encoder.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

from typing import Any
import numpy as np


def encode_terrain_rgb(elevation_data: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    """
    Encode elevation data into RGB values using Mapbox Terrain-RGB formula.
    height = -10000 + ((R * 65536 + G * 256 + B) * 0.1)
    ==> (height + 10000) * 10 = R * 65536 + G * 256 + B

    Returns an (H, W, 3) uint8 array.
    """
    # Clip and handle no-data (we use Alpha for mask, but RGB should be base)
    # Mapbox standard base is -10000
    v = ((elevation_data + 10000) * 10).astype(np.int32)
    v = np.clip(v, 0, 0xFFFFFF)  # 24-bit range

    r = (v // 65536).astype(np.uint8)
    g = ((v % 65536) // 256).astype(np.uint8)
    b = (v % 256).astype(np.uint8)

    return np.stack((r, g, b), axis=-1)
