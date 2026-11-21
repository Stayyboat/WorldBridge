from pathlib import Path

ENGINE = Path("engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java")
VIEW = Path("app/src/main/java/com/worldbridge/app/WorldPreviewView.java")

engine = ENGINE.read_text()
view = VIEW.read_text()


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


# Keep the End origin and central island inside the initial viewport even when
# no generated End chunks have been saved yet.
engine = replace_once(
    engine,
    """        if (state.columns.isEmpty()) {
            return new PreviewData(tiles, 0, -1, 0, -1, dimensionId, false, false, player);
        }
        return new PreviewData(tiles, state.minX, state.maxX, state.minZ, state.maxZ,
                dimensionId, hasBiomeOrHeightData, hasBlockData, player);""",
    """        if (state.columns.isEmpty()) {
            if (dimensionId == 2) {
                return new PreviewData(tiles, -7, 7, -7, 7, dimensionId, false, false, player);
            }
            return new PreviewData(tiles, 0, -1, 0, -1, dimensionId, false, false, player);
        }
        int minX = state.minX, maxX = state.maxX;
        int minZ = state.minZ, maxZ = state.maxZ;
        if (dimensionId == 2) {
            minX = Math.min(minX, -7);
            maxX = Math.max(maxX, 7);
            minZ = Math.min(minZ, -7);
            maxZ = Math.max(maxZ, 7);
        }
        return new PreviewData(tiles, minX, maxX, minZ, maxZ,
                dimensionId, hasBiomeOrHeightData, hasBlockData, player);""",
    "End preview bounds"
)

engine = replace_once(
    engine,
    """            if (remaining.isEmpty()) return new PreviewData(remaining, 0, -1, 0, -1,
                    dimensionId, hasBiomeOrHeightData, hasBlockData, null);
            PlayerPosition player = hasPlayerPosition
                    ? new PlayerPosition(playerX, 0, playerZ, playerYaw, playerDimensionId) : null;
            return new PreviewData(remaining, minX, maxX, minZ, maxZ,
                    dimensionId, hasBiomeOrHeightData, hasBlockData, player);""",
    """            if (remaining.isEmpty()) {
                if (dimensionId == 2) {
                    return new PreviewData(remaining, -7, 7, -7, 7,
                            dimensionId, hasBiomeOrHeightData, hasBlockData, null);
                }
                return new PreviewData(remaining, 0, -1, 0, -1,
                        dimensionId, hasBiomeOrHeightData, hasBlockData, null);
            }
            PlayerPosition player = hasPlayerPosition
                    ? new PlayerPosition(playerX, 0, playerZ, playerYaw, playerDimensionId) : null;
            if (dimensionId == 2) {
                minX = Math.min(minX, -7);
                maxX = Math.max(maxX, 7);
                minZ = Math.min(minZ, -7);
                maxZ = Math.max(maxZ, 7);
            }
            return new PreviewData(remaining, minX, maxX, minZ, maxZ,
                    dimensionId, hasBiomeOrHeightData, hasBlockData, player);""",
    "End preview bounds after pruning"
)
ENGINE.write_text(engine)


# The End main island is a generated visual overlay, not a synthetic chunk record.
# Missing saved chunks inside its footprint get End-stone colouring; real saved
# chunk tiles always take precedence.
view = replace_once(
    view,
    "        if (preview == null || preview.tiles.isEmpty() || getWidth() <= 0 || getHeight() <= 0) return;",
    "        if (preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2) || getWidth() <= 0 || getHeight() <= 0) return;",
    "fit End preview with no saved chunks"
)

view = replace_once(
    view,
    """        if (preview.tiles.isEmpty()) {
            drawCentered(canvas, "No saved chunks in this dimension", 13, 0xFF9DAEC3);
            return;
        }""",
    """        if (preview.tiles.isEmpty() && preview.dimensionId != 2) {
            drawCentered(canvas, "No saved chunks in this dimension", 13, 0xFF9DAEC3);
            return;
        }""",
    "allow End visual overlay without saved chunks"
)

view = replace_once(
    view,
    """        drawPlayerMarker(canvas);
        paint.setStyle(Paint.Style.STROKE);""",
    """        drawPlayerMarker(canvas);
        if (preview.dimensionId == 2) drawEndOriginMarker(canvas);
        paint.setStyle(Paint.Style.STROKE);""",
    "End origin marker draw call"
)

view = replace_once(
    view,
    "        if (data == null || data.tiles == null || data.tiles.isEmpty()) return null;",
    "        if (data == null || data.tiles == null || (data.tiles.isEmpty() && data.dimensionId != 2)) return null;",
    "create empty End overview"
)

# Paint the fixed central-island silhouette into overview pixels only where there
# is no actual saved chunk data, preserving all actual preview detail.
view = replace_once(
    view,
    """        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
    }

    private static int averageTile(int[] colors) {""",
    """        }
        if (data.dimensionId == 2) {
            for (int y = 0; y < height; y++) {
                double worldChunkZ = data.minChunkZ + ((y + 0.5) * worldH / height);
                int blockZ = (int) Math.floor(worldChunkZ * 16.0);
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (counts[index] != 0) continue;
                    double worldChunkX = data.minChunkX + ((x + 0.5) * worldW / width);
                    int blockX = (int) Math.floor(worldChunkX * 16.0);
                    int islandColor = endIslandColorAtBlock(blockX, blockZ);
                    if (islandColor != 0) pixels[index] = islandColor;
                }
            }
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
    }

    private static int averageTile(int[] colors) {""",
    "End island in overview bitmap"
)

view = replace_once(
    view,
    "        if (preview == null || preview.tiles.isEmpty()) return;",
    "        if (preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2)) return;",
    "draw End buckets when empty"
)

# For missing chunks, draw a deterministic, irregular End-stone footprint around
# block coordinate 0,0 instead of treating that entire area as void checkerboard.
view = replace_once(
    view,
    """                if (tile == null || tile.length == 0) {
                    int color = ((worldX ^ worldZ) & 1) == 0 ? 0xFF343434 : 0xFF414141;
                    for (int row = 0; row < 16; row++) java.util.Arrays.fill(pixels, (offsetY + row) * BUCKET_PIXELS + offsetX,
                            (offsetY + row) * BUCKET_PIXELS + offsetX + 16, color);
                } else if (tile.length >= 256) {""",
    """                if (tile == null || tile.length == 0) {
                    int voidColor = ((worldX ^ worldZ) & 1) == 0 ? 0xFF343434 : 0xFF414141;
                    for (int row = 0; row < 16; row++) {
                        for (int col = 0; col < 16; col++) {
                            int islandColor = preview.dimensionId == 2
                                    ? endIslandColorAtBlock(worldX * 16 + col, worldZ * 16 + row) : 0;
                            pixels[(offsetY + row) * BUCKET_PIXELS + offsetX + col] =
                                    islandColor != 0 ? islandColor : voidColor;
                        }
                    }
                } else if (tile.length >= 256) {""",
    "End island in chunk bucket bitmap"
)

# Add a small, always-visible origin symbol at block coordinates (0,0) in the End.
anchor = "    private void drawPlayerMarker(Canvas canvas) {\n"
if view.count(anchor) != 1:
    raise SystemExit("Could not find marker helper insertion point")

helpers = """    private static int endIslandColorAtBlock(int blockX, int blockZ) {
        // The Bedrock End's central island is centred around 0,0. This is an
        // approximate footprint for unpersisted chunks; saved chunk data wins.
        double nx = blockX / 98.0;
        double nz = blockZ / 92.0;
        double angle = Math.atan2(nz, nx);
        double radius = Math.sqrt(nx * nx + nz * nz);
        double edge = 1.0
                + 0.040 * Math.sin(angle * 3.0 + 0.45)
                + 0.027 * Math.cos(angle * 7.0 - 0.8)
                + 0.016 * Math.sin(angle * 11.0 + 1.2);
        if (radius > edge) return 0;

        int noise = blockX * 0x45D9F3B ^ blockZ * 0x119DE1F3;
        noise ^= (noise >>> 16);
        int variation = ((noise >>> 27) & 15) - 7;
        boolean rim = radius > edge - 0.075;
        int red = (rim ? 190 : 216) + variation;
        int green = (rim ? 179 : 207) + variation;
        int blue = (rim ? 128 : 151) + variation / 2;
        red = Math.max(0, Math.min(255, red));
        green = Math.max(0, Math.min(255, green));
        blue = Math.max(0, Math.min(255, blue));
        return 0xFF000000 | (red << 16) | (green << 8) | blue;
    }

    private void drawEndOriginMarker(Canvas canvas) {
        float x = mapLeft;
        float y = mapTop;
        float radius = dp(4.2f);
        if (x < -radius || y < -radius || x > getWidth() + radius || y > getHeight() + radius) return;

        paint.setStyle(Paint.Style.FILL);
        paint.setShadowLayer(dp(2), 0, dp(1), 0xCC000000);
        paint.setColor(0xFFF1EFF5);
        canvas.drawCircle(x, y, radius, paint);
        paint.clearShadowLayer();
        paint.setColor(0xFFB69CFF);
        canvas.drawCircle(x, y, dp(2.15f), paint);

        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(dp(1.1f));
        paint.setColor(0xFFE7DFFF);
        canvas.drawCircle(x, y, radius + dp(1.1f), paint);
        paint.setStyle(Paint.Style.FILL);

        if (scale >= dp(8f)) {
            paint.setTextSize(dp(8f));
            paint.setTypeface(android.graphics.Typeface.create(
                    "sans-serif-medium", android.graphics.Typeface.NORMAL));
            paint.setTextAlign(Paint.Align.LEFT);
            paint.setColor(0xFFF1EFF5);
            canvas.drawText("0,0", x + dp(6), y - dp(5), paint);
            paint.setTextAlign(Paint.Align.LEFT);
        }
    }

"""
view = view.replace(anchor, helpers + anchor, 1)

view = replace_once(
    view,
    "        if (scaling || preview == null || preview.tiles.isEmpty()) return true;",
    "        if (scaling || preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2)) return true;",
    "allow End area selection without saved chunks"
)

VIEW.write_text(view)
print("Added an approximate central End-island visual overlay and a persistent 0,0 origin marker. No synthetic chunk records are added; real saved chunk tiles take priority.")
