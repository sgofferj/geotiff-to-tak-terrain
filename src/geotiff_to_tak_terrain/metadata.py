#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# metadata.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

import json
import zlib
import struct
from typing import Dict, Any


def create_taka_chunk(metadata: Dict[str, Any]) -> bytes:
    """
    Create a custom PNG 'tAKa' chunk containing JSON metadata.
    Chunk format: Length (4 bytes), Type ('tAKa', 4 bytes), Data (Length bytes), CRC (4 bytes).
    """
    data = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    chunk_type = b"tAKa"
    length = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return length + chunk_type + data + crc
