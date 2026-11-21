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


# Keep the End origin in the initial viewport, but never draw terrain that is
# not present in the imported world's saved chunk data.
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


# Allow an empty End viewport so the 0,0 marker remains visible; absent chunks
# stay void instead of being painted as a guessed central island.
view = replace_once(
    view,
    "        if (preview == null || preview.tiles.isEmpty() || getWidth() <= 0 || getHeight() <= 0) return;",
    "        if (preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2) || getWidth() <= 0 || getHeight() <= 0) return;",
    "fit empty End preview"
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
    "keep End origin visible without saved chunks"
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

view = replace_once(
    view,
    "        if (preview == null || preview.tiles.isEmpty()) return;",
    "        if (preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2)) return;",
    "draw empty End viewport"
)

# Retain the small 0,0 locator marker only. No island shape or block colours are
# generated; all visible End terrain must originate from actual saved chunk data.
anchor = "    private void drawPlayerMarker(Canvas canvas) {\n"
if view.count(anchor) != 1:
    raise SystemExit("Could not find marker helper insertion point")

helper = """    private void drawEndOriginMarker(Canvas canvas) {
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
view = view.replace(anchor, helper + anchor, 1)

view = replace_once(
    view,
    "        if (scaling || preview == null || preview.tiles.isEmpty()) return true;",
    "        if (scaling || preview == null || (preview.tiles.isEmpty() && preview.dimensionId != 2)) return true;",
    "allow End origin selection viewport"
)

VIEW.write_text(view)
print("Removed the synthetic End central-island overlay. The End preview now shows only saved terrain plus the 0,0 marker.")
