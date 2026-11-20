from pathlib import Path

p = Path("app/src/main/java/com/worldbridge/app/WorldPreviewView.java")
s = p.read_text()
s = s.replace("import android.graphics.Canvas;", "import android.graphics.Bitmap;\nimport android.graphics.Canvas;")
s = s.replace("import java.util.Map;", "import java.util.Map;\nimport java.util.HashMap;\nimport java.util.Iterator;")

s = s.replace(
    "    private BedrockWorldPreview.PreviewData preview;",
    "    private BedrockWorldPreview.PreviewData preview;\n    private final HashMap<Long, Bitmap> tileBitmaps = new HashMap<>();"
)
s = s.replace(
    "        this.preview = preview;\n        needsFit = true;",
    "        this.preview = preview;\n        tileBitmaps.clear();\n        needsFit = true;"
)

start = s.index("        float chunkSize = scale;")
end = s.index("\n        drawChunkGridAndLabels(canvas);", start)
replacement = """        float chunkSize = scale;
        drawMissingChunkCheckerboard(canvas);
        drawVisibleChunkBitmaps(canvas, chunkSize);
"""
s = s[:start] + replacement + s[end:]

insert = s.index("    private void drawMissingChunkCheckerboard(Canvas canvas)")
methods = """    private void drawVisibleChunkBitmaps(Canvas canvas, float chunkSize) {
        if (preview == null || preview.tiles.isEmpty()) return;
        int left = Math.max(preview.minChunkX, (int) Math.floor((-mapLeft) / chunkSize));
        int right = Math.min(preview.maxChunkX, (int) Math.floor((getWidth() - mapLeft) / chunkSize));
        int top = Math.max(preview.minChunkZ, (int) Math.floor((-mapTop) / chunkSize));
        int bottom = Math.min(preview.maxChunkZ, (int) Math.floor((getHeight() - mapTop) / chunkSize));
        if (right < left || bottom < top) return;

        paint.setStyle(Paint.Style.FILL);
        paint.setFilterBitmap(chunkSize < dp(16f));
        paint.setDither(false);
        for (int cz = top; cz <= bottom; cz++) {
            float dstTop = mapTop + cz * chunkSize;
            for (int cx = left; cx <= right; cx++) {
                long key = (((long) cx) << 32) | (cz & 0xFFFFFFFFL);
                int[] pixels = preview.tiles.get(key);
                if (pixels == null) continue;
                Bitmap tile = tileBitmaps.get(key);
                if (tile == null || tile.isRecycled()) {
                    tile = makeTileBitmap(pixels);
                    if (tile != null) {\n                        tileBitmaps.put(key, tile);\n                        if (tileBitmaps.size() > 512) {\n                            Iterator<Map.Entry<Long, Bitmap>> it = tileBitmaps.entrySet().iterator();\n                            if (it.hasNext()) { Bitmap old = it.next().getValue(); it.remove(); if (old != null && !old.isRecycled()) old.recycle(); }\n                        }\n                    }
                }
                if (tile != null) {
                    float dstLeft = mapLeft + cx * chunkSize;
                    rect.set(dstLeft, dstTop, dstLeft + chunkSize + 0.25f, dstTop + chunkSize + 0.25f);
                    canvas.drawBitmap(tile, null, rect, paint);
                }
            }
        }
        paint.setFilterBitmap(false);
    }

    private Bitmap makeTileBitmap(int[] pixels) {
        if (pixels == null || pixels.length == 0) return null;
        int[] blockPixels = new int[256];
        if (pixels.length >= 256) {
            System.arraycopy(pixels, 0, blockPixels, 0, 256);
        } else if (pixels.length >= 16) {
            for (int z = 0; z < 16; z++) for (int x = 0; x < 16; x++)
                blockPixels[z * 16 + x] = pixels[(z / 4) * 4 + (x / 4)];
        } else {
            int color = average(pixels);
            java.util.Arrays.fill(blockPixels, color);
        }
        return Bitmap.createBitmap(blockPixels, 16, 16, Bitmap.Config.ARGB_8888);
    }

"""
s = s[:insert] + methods + s[insert:]

# The bitmap cache is derived from immutable preview data; don't retain it after detaching.
detach = s.index("    @Override\n    protected void onMeasure")
s = s[:detach] + """    @Override
    protected void onDetachedFromWindow() {
        for (Bitmap bitmap : tileBitmaps.values()) if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();
        tileBitmaps.clear();
        super.onDetachedFromWindow();
    }

""" + s[detach:]

p.write_text(s)
print("Cached visible chunk bitmap renderer applied")
