# Why do the tiles look so weird?

If you open one of these Terrain-RGB tiles in a standard image viewer, you'll see a psychedelic "glitch" of colors instead of a normal grayscale elevation map. This is by design!

### The 24-bit Packing Trick
Standard 8-bit grayscale images only have 256 levels (0–255). If 1 unit = 1 meter, you could only represent a mountain 256 meters high. To cover the entire planet with **centimeter precision**, the elevation is "spread" across the **Red, Green, and Blue** channels of a 24-bit PNG.

The formula used to decode the height is:
**Height (meters) = -10000 + ((R * 65536 + G * 256 + B) * 0.1)**

### What You're Seeing
- **Red (R):** Large steps of **6,553.6 meters**.
- **Green (G):** Medium steps of **25.6 meters**.
- **Blue (B):** Fine steps of **0.1 meters (10 centimeters)**.

This is why a simple slope looks like a rapidly cycling blue gradient—the blue channel is "overflowing" and resetting every 10cm to keep the precision high. When the slope is steep enough, the green channel jumps, creating the "step" effect.

### Why use this for TAK?
This format is known as **LCLL (Low Complexity, Low Latency)**. Because the elevation is just a simple math formula on three numbers, a mobile device (like an Android phone running ATAK) can instantly calculate the height of any pixel without needing a complex GIS engine. It's high-precision elevation data disguised as a standard image!
