#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_generate_config.py from https://github.com/sgofferj/geotiff-to-tak-terrain
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

"""Regression tests for the generated TAK streaming-tiles config.json.

ATAK's StreamingTiles parser calls getDouble("minX"/"minY"/"maxX"/"maxY") and
returns null on any JSONException, which makes it silently reject the whole
config. Using minLon/minLat/maxLon/maxLat (as we did before) therefore broke
terrain import in ATAK.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from geotiff_to_tak_terrain.config import ConfigParams, generate_config  # noqa: E402


class GenerateConfigTest(unittest.TestCase):
    def _generate(self, extent=None, max_z=14):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        generate_config(
            ConfigParams(
                output_dir=tmpdir.name,
                title="Test Terrain",
                data_source="Test DEM",
                heights="hae",
                max_z=max_z,
                extent=extent,
            )
        )
        with open(
            os.path.join(tmpdir.name, "config.json"), encoding="utf-8"
        ) as f:
            return json.load(f)

    def test_bounds_use_tak_key_names(self):
        extent = (15.0, 59.0, 33.0, 70.0)
        config = self._generate(extent=extent)

        self.assertEqual(
            config["bounds"],
            {"minX": 15.0, "minY": 59.0, "maxX": 33.0, "maxY": 70.0},
        )
        for legacy_key in ("minLon", "minLat", "maxLon", "maxLat"):
            self.assertNotIn(legacy_key, config["bounds"])

    def test_terrain_content(self):
        config = self._generate()

        self.assertEqual(config["content"], "terrain")
        self.assertEqual(config["mimeType"], "application/vnd.mapbox-terrain-rgb")
        self.assertEqual(config["srs"], "EPSG:4326")
        self.assertTrue(config["isQuadtree"])
        self.assertEqual(config["numLevels"], 15)


if __name__ == "__main__":
    unittest.main()
