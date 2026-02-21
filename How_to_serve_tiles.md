# Serving Terrain Tiles to ATAK

So, you want to serve terrain tiles to ATAK? Whether you're using the fancy Cesium Quantized Mesh or the classic "LCLL" PNG format, here’s the lowdown on how it works and how to set it up.

## 1. The Two Main Formats

ATAK natively supports two main streaming terrain formats through its "Streaming Tiles" interface:

### A. Cesium Quantized Mesh (`.terrain`)
*   **MIME Type**: `application/vnd.quantized-mesh`
*   **What it is**: A binary geometry format. Great for 3D performance.
*   **Tiling**: Usually follows the **TMS** scheme (Y=0 is at the South Pole).
*   **Gotcha**: ATAK's native C++ parser **hates** gzip-compressed HTTP bodies. If you store them zipped, Nginx must decompress them before sending them to ATAK.

### B. "LCLL" / Mapbox Terrain-RGB (`.png`)
*   **MIME Type**: `application/vnd.mapbox-terrain-rgb`
*   **Encoding**: 8-bit RGBA PNG. Elevation is packed into RGB:
    `height = -10000 + ((R * 65536 + G * 256 + B) * 0.1)`
*   **Secret Sauce**: ATAK looks for a custom PNG chunk called `tAKa`. It contains a tiny JSON string with metadata like the SRID and tile index.
*   **Tiling**: Usually follows the **Slippy/Google** scheme (Y=0 is at the North Pole). For `EPSG:4326`, Level 0 consists of **two** tiles (X=0 for West, X=1 for East).

---

## 2. Tileserver Structure

ATAK builds its 3D globe from the ground up. This means:
1.  **Start at the Root**: ATAK will **always** request the Zoom Level 0 tiles first to establish the base shape of the Earth. If Zoom 0 is missing, the whole layer often fails to load.
2.  **The Directory Tree**: Tiles should be stored as `{z}/{x}/{y}.extension`.
3.  **The Bounds**: Even if you define `bounds` in your config, ATAK might still poke at parent tiles. It uses the bounds to decide which *high-zoom* tiles to fetch.

---

## 3. Nginx Configuration

This is where the magic happens. ATAK's native engine doesn't handle decompression well, but web browsers (like CesiumJS) love it.

### Step 1: Fix MIME Types
Add these to your `/etc/nginx/mime.types` or inside your `http` block:
```nginx
types {
    application/vnd.quantized-mesh  terrain;
    application/vnd.mapbox-terrain-rgb  png;
}
```

### Step 2: The "TAK vs Browser" Gzip Logic
If you store your tiles **uncompressed** on disk, use this config. It compresses tiles for browsers but serves them raw to ATAK:

```nginx
server {
    ...
    location /cesium/ {
        gzip on;
        gzip_types application/vnd.quantized-mesh application/vnd.mapbox-terrain-rgb;

        # Disable compression specifically for ATAK
        gzip_disable "TAK";

        # Ensure proxies don't cache the wrong version
        gzip_vary on;

        # Standard CORS for web users
        add_header Access-Control-Allow-Origin *;
    }
}
```

---

## 4. The `config.json`

This is the file you actually import into ATAK.

```json
{
  "schema": "2.1.0",
  "title": "My Terrain",
  "content": "terrain",
  "mimeType": "application/vnd.quantized-mesh",
  "url": "https://myserver.com/tiles/{$z}/{$x}/{$y}.terrain",
  "srs": "EPSG:4326",
  "isQuadtree": true,
  "invertYAxis": true,
  "numLevels": 14,
  "bounds": {
    "minX": 15.0, "minY": 59.0, "maxX": 33.0, "maxY": 70.0
  }
}
```
*   **`invertYAxis`**: Set to `true` for TMS (standard for Cesium Mesh), and `false` for Slippy (standard for most PNG setups).
*   **`isQuadtree`**: Tells ATAK it can calculate the resolutions of higher zooms based on the Level 0 definition.

## Summary Checklist
- [ ] Level 0 tiles exist.
- [ ] No-data areas in PNGs have Alpha = 0.
- [ ] Nginx is not serving gzipped bodies to the "TAK" User-Agent.
- [ ] `mimeType` in config matches the actual data format.
