from pathlib import Path

view_path = Path('app/src/main/java/com/worldbridge/app/WorldPreviewView.java')
s = view_path.read_text()

# Bitmap-based LOD rendering: one overview image at low zoom, cached 32x32-chunk
# composite tiles at high zoom. This avoids thousands of per-chunk Canvas calls.
s = s.replace('import android.graphics.Canvas;', 'import android.graphics.Canvas;')
s = s.replace('import java.util.Iterator;', 'import java.util.Iterator;\nimport java.util.LinkedHashMap;')
s = s.replace('    private final HashMap<Long, Bitmap> tileBitmaps = new HashMap<>();', '''    private Bitmap overviewBitmap;
    private final LinkedHashMap<Long, Bitmap> bucketBitmaps = new LinkedHashMap<Long, Bitmap>(20, 0.75f, true);
    private final Path gridPath = new Path();
    private static final int BUCKET_CHUNKS = 32;
    private static final int BUCKET_PIXELS = BUCKET_CHUNKS * 16;
    private static final int MAX_BUCKET_BITMAPS = 8;
    private static final float DETAIL_ZOOM_DP = 6f;''')

old = '''    public void setPreview(BedrockWorldPreview.PreviewData preview) {
        this.preview = preview;
        tileBitmaps.clear();
        needsFit = true;
        requestLayout();
        invalidate();
    }'''
new = '''    public void setPreview(BedrockWorldPreview.PreviewData preview, Bitmap overviewBitmap) {
        recycleBucketBitmaps();
        if (this.overviewBitmap != null && this.overviewBitmap != overviewBitmap && !this.overviewBitmap.isRecycled()) this.overviewBitmap.recycle();
        this.preview = preview;
        this.overviewBitmap = overviewBitmap;
        needsFit = true;
        requestLayout();
        invalidate();
    }

    private void recycleBucketBitmaps() {
        for (Bitmap bitmap : bucketBitmaps.values()) if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();
        bucketBitmaps.clear();
    }'''
assert old in s
s = s.replace(old, new)

old = '''    @Override
    protected void onDetachedFromWindow() {
        for (Bitmap bitmap : tileBitmaps.values()) if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();
        tileBitmaps.clear();
        super.onDetachedFromWindow();
    }'''
new = '''    @Override
    protected void onDetachedFromWindow() {
        recycleBucketBitmaps();
        if (overviewBitmap != null && !overviewBitmap.isRecycled()) overviewBitmap.recycle();
        overviewBitmap = null;
        super.onDetachedFromWindow();
    }'''
assert old in s
s = s.replace(old, new)

start = s.index('        float chunkSize = scale;')
end = s.index('\n        drawChunkGridAndLabels(canvas);', start)
new_draw = '''        float chunkSize = scale;
        if (chunkSize < dp(DETAIL_ZOOM_DP) && overviewBitmap != null && !overviewBitmap.isRecycled()) {
            drawOverview(canvas);
        } else {
            drawVisibleBuckets(canvas, chunkSize);
        }
'''
s = s[:start] + new_draw + s[end:]

start = s.index('    private void drawVisibleChunkBitmaps(')
end = s.index('    private void drawChunkGridAndLabels(', start)
methods = r'''    /** Builds a compact low-zoom image. Call from the background worker, never the UI thread. */
    public static Bitmap createOverviewBitmap(BedrockWorldPreview.PreviewData data) {
        if (data == null || data.tiles == null || data.tiles.isEmpty()) return null;
        long worldW = Math.max(1L, (long) data.maxChunkX - data.minChunkX + 1L);
        long worldH = Math.max(1L, (long) data.maxChunkZ - data.minChunkZ + 1L);
        double factor = Math.min(4.0, 1024.0 / Math.max(worldW, worldH));
        int width = Math.max(1, (int) Math.ceil(worldW * factor));
        int height = Math.max(1, (int) Math.ceil(worldH * factor));
        int[] pixels = new int[width * height];
        byte[] counts = new byte[pixels.length];
        for (int y = 0; y < height; y++) {
            int row = y * width;
            for (int x = 0; x < width; x++) pixels[row + x] = ((x ^ y) & 1) == 0 ? 0xFF343434 : 0xFF414141;
        }
        for (Map.Entry<Long, int[]> entry : data.tiles.entrySet()) {
            long key = entry.getKey();
            int cx = (int) (key >> 32), cz = (int) key;
            int px = (int) (((long) cx - data.minChunkX) * width / worldW);
            int py = (int) (((long) cz - data.minChunkZ) * height / worldH);
            if (px < 0 || px >= width || py < 0 || py >= height) continue;
            int color = averageTile(entry.getValue());
            int index = py * width + px;
            int count = counts[index] & 0xFF;
            if (count == 0) {
                pixels[index] = color;
                counts[index] = 1;
            } else {
                int old = pixels[index];
                int nextCount = Math.min(255, count + 1);
                int r = ((((old >>> 16) & 255) * count) + ((color >>> 16) & 255)) / (count + 1);
                int g = ((((old >>> 8) & 255) * count) + ((color >>> 8) & 255)) / (count + 1);
                int b = (((old & 255) * count) + (color & 255)) / (count + 1);
                pixels[index] = 0xFF000000 | (r << 16) | (g << 8) | b;
                counts[index] = (byte) nextCount;
            }
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
    }

    private static int averageTile(int[] colors) {
        if (colors == null || colors.length == 0) return 0xFF777777;
        long r = 0, g = 0, b = 0;
        int count = Math.min(colors.length, 256);
        for (int i = 0; i < count; i++) {
            int c = colors[i];
            r += (c >>> 16) & 255;
            g += (c >>> 8) & 255;
            b += c & 255;
        }
        return 0xFF000000 | ((int)(r / count) << 16) | ((int)(g / count) << 8) | (int)(b / count);
    }

    private void drawOverview(Canvas canvas) {
        float left = mapLeft + preview.minChunkX * scale;
        float top = mapTop + preview.minChunkZ * scale;
        float right = mapLeft + (preview.maxChunkX + 1f) * scale;
        float bottom = mapTop + (preview.maxChunkZ + 1f) * scale;
        rect.set(left, top, right, bottom);
        paint.setStyle(Paint.Style.FILL);
        paint.setFilterBitmap(true);
        paint.setDither(false);
        canvas.drawBitmap(overviewBitmap, null, rect, paint);
        paint.setFilterBitmap(false);
    }

    private void drawVisibleBuckets(Canvas canvas, float chunkSize) {
        if (preview == null || preview.tiles.isEmpty()) return;
        int left = Math.max(preview.minChunkX, (int)Math.floor(-mapLeft / chunkSize));
        int right = Math.min(preview.maxChunkX, (int)Math.floor((getWidth() - mapLeft) / chunkSize));
        int top = Math.max(preview.minChunkZ, (int)Math.floor(-mapTop / chunkSize));
        int bottom = Math.min(preview.maxChunkZ, (int)Math.floor((getHeight() - mapTop) / chunkSize));
        if (right < left || bottom < top) return;
        int bucketLeft = Math.floorDiv(left, BUCKET_CHUNKS);
        int bucketRight = Math.floorDiv(right, BUCKET_CHUNKS);
        int bucketTop = Math.floorDiv(top, BUCKET_CHUNKS);
        int bucketBottom = Math.floorDiv(bottom, BUCKET_CHUNKS);
        float worldLeft = mapLeft + preview.minChunkX * chunkSize;
        float worldTop = mapTop + preview.minChunkZ * chunkSize;
        float worldRight = mapLeft + (preview.maxChunkX + 1f) * chunkSize;
        float worldBottom = mapTop + (preview.maxChunkZ + 1f) * chunkSize;
        int save = canvas.save();
        canvas.clipRect(worldLeft, worldTop, worldRight, worldBottom);
        paint.setStyle(Paint.Style.FILL);
        paint.setFilterBitmap(chunkSize < dp(16f));
        paint.setDither(false);
        for (int bz = bucketTop; bz <= bucketBottom; bz++) {
            for (int bx = bucketLeft; bx <= bucketRight; bx++) {
                long bucketKey = (((long) bx) << 32) | (bz & 0xFFFFFFFFL);
                Bitmap bitmap = bucketBitmaps.get(bucketKey);
                if (bitmap == null || bitmap.isRecycled()) {
                    bitmap = makeBucketBitmap(bx, bz);
                    if (bitmap != null) {
                        bucketBitmaps.put(bucketKey, bitmap);
                        while (bucketBitmaps.size() > MAX_BUCKET_BITMAPS) {
                            Iterator<Map.Entry<Long, Bitmap>> it = bucketBitmaps.entrySet().iterator();
                            if (!it.hasNext()) break;
                            Bitmap old = it.next().getValue();
                            it.remove();
                            if (old != null && !old.isRecycled()) old.recycle();
                        }
                    }
                }
                if (bitmap != null) {
                    float chunkX = bx * (float) BUCKET_CHUNKS;
                    float chunkZ = bz * (float) BUCKET_CHUNKS;
                    rect.set(mapLeft + chunkX * chunkSize, mapTop + chunkZ * chunkSize,
                            mapLeft + (chunkX + BUCKET_CHUNKS) * chunkSize,
                            mapTop + (chunkZ + BUCKET_CHUNKS) * chunkSize);
                    canvas.drawBitmap(bitmap, null, rect, paint);
                }
            }
        }
        canvas.restoreToCount(save);
        paint.setFilterBitmap(false);
    }

    private Bitmap makeBucketBitmap(int bucketX, int bucketZ) {
        int[] pixels = new int[BUCKET_PIXELS * BUCKET_PIXELS];
        int startChunkX = bucketX * BUCKET_CHUNKS;
        int startChunkZ = bucketZ * BUCKET_CHUNKS;
        for (int cz = 0; cz < BUCKET_CHUNKS; cz++) {
            for (int cx = 0; cx < BUCKET_CHUNKS; cx++) {
                int worldX = startChunkX + cx;
                int worldZ = startChunkZ + cz;
                long key = (((long) worldX) << 32) | (worldZ & 0xFFFFFFFFL);
                int[] tile = preview.tiles.get(key);
                int offsetX = cx * 16;
                int offsetY = cz * 16;
                if (tile == null || tile.length == 0) {
                    int color = ((worldX ^ worldZ) & 1) == 0 ? 0xFF343434 : 0xFF414141;
                    for (int row = 0; row < 16; row++) java.util.Arrays.fill(pixels, (offsetY + row) * BUCKET_PIXELS + offsetX,
                            (offsetY + row) * BUCKET_PIXELS + offsetX + 16, color);
                } else if (tile.length >= 256) {
                    for (int row = 0; row < 16; row++) System.arraycopy(tile, row * 16, pixels,
                            (offsetY + row) * BUCKET_PIXELS + offsetX, 16);
                } else if (tile.length >= 16) {
                    for (int row = 0; row < 16; row++) for (int col = 0; col < 16; col++)
                        pixels[(offsetY + row) * BUCKET_PIXELS + offsetX + col] = tile[(row / 4) * 4 + (col / 4)];
                } else {
                    int color = averageTile(tile);
                    for (int row = 0; row < 16; row++) java.util.Arrays.fill(pixels, (offsetY + row) * BUCKET_PIXELS + offsetX,
                            (offsetY + row) * BUCKET_PIXELS + offsetX + 16, color);
                }
            }
        }
        return Bitmap.createBitmap(pixels, BUCKET_PIXELS, BUCKET_PIXELS, Bitmap.Config.ARGB_8888);
    }

'''
s = s[:start] + methods + s[end:]

# Grid draw calls are consolidated into one Path; coordinate labels are sampled/capped.
start = s.index('    private void drawChunkGridAndLabels(Canvas canvas) {')
end = s.index('\n    private void drawSelection(Canvas canvas)', start)
new_grid = r'''    private void drawChunkGridAndLabels(Canvas canvas) {
        if (preview == null || scale < dp(7f)) return;
        int left = Math.max(preview.minChunkX, (int)Math.floor(-mapLeft / scale));
        int right = Math.min(preview.maxChunkX + 1, (int)Math.ceil((getWidth() - mapLeft) / scale));
        int top = Math.max(preview.minChunkZ, (int)Math.floor(-mapTop / scale));
        int bottom = Math.min(preview.maxChunkZ + 1, (int)Math.ceil((getHeight() - mapTop) / scale));
        gridPath.reset();
        for (int cx = left; cx <= right; cx++) {
            float x = mapLeft + cx * scale;
            gridPath.moveTo(x, mapTop + top * scale);
            gridPath.lineTo(x, mapTop + bottom * scale);
        }
        for (int cz = top; cz <= bottom; cz++) {
            float y = mapTop + cz * scale;
            gridPath.moveTo(mapLeft + left * scale, y);
            gridPath.lineTo(mapLeft + right * scale, y);
        }
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(Math.max(0.5f, dp(0.65f)));
        paint.setColor(0x99D7D7D7);
        canvas.drawPath(gridPath, paint);
        paint.setStyle(Paint.Style.FILL);
        if (scale >= dp(30f)) {
            paint.setTextSize(dp(8f));
            paint.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
            paint.setColor(0xFFEAEAEA);
            int step = Math.max(1, (int)Math.ceil(Math.max(right - left, bottom - top) / 10f));
            int drawn = 0;
            for (int cz = top; cz < bottom && drawn < 100; cz += step) {
                for (int cx = left; cx < right && drawn < 100; cx += step) {
                    float x = mapLeft + cx * scale + dp(2f);
                    float y = mapTop + cz * scale + dp(10f);
                    if (x < getWidth() && y > 0 && y < getHeight()) {
                        canvas.drawText("(" + (cx * 16) + ", " + (cz * 16) + ")", x, y, paint);
                        drawn++;
                    }
                }
            }
        }
    }
'''
s = s[:start] + new_grid + s[end:]

# Remove imports left over from the previous single-chunk cache.
s = s.replace('import java.util.HashMap;\n', '')
view_path.write_text(s)

# Build the overview image off the main thread after scanning, then pass it to the view.
activity_path = Path('app/src/main/java/com/worldbridge/app/MainActivity.java')
a = activity_path.read_text()
if 'import android.graphics.Bitmap;' not in a:
    a = a.replace('package com.worldbridge.app;\n', 'package com.worldbridge.app;\n\nimport android.graphics.Bitmap;')
old = '''                BedrockWorldPreview.PreviewData data = BedrockWorldPreview.scan(workingWorld, dimensionId);
                runOnUiThread(() -> {
                    if (requestId != previewRequestId || !worldLoaded) return;
                    mapView.setPreview(data);'''
new = '''                BedrockWorldPreview.PreviewData data = BedrockWorldPreview.scan(workingWorld, dimensionId);
                Bitmap overview = WorldPreviewView.createOverviewBitmap(data);
                runOnUiThread(() -> {
                    if (requestId != previewRequestId || !worldLoaded) {
                        if (overview != null && !overview.isRecycled()) overview.recycle();
                        return;
                    }
                    mapView.setPreview(data, overview);'''
assert old in a, 'MainActivity preview success block not found'
a = a.replace(old, new)
a = a.replace('                    mapView.setPreview(null);', '                    mapView.setPreview(null, null);')
activity_path.write_text(a)
print('Applied LOD overview + 32x32 chunk bucket renderer')
