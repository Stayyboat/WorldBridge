from pathlib import Path

engine = Path("engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java")
s = engine.read_text()
s = s.replace(
    "} else if (false) { // fast-preview mode: defer expensive subchunk palette decoding",
    "} else if (isSubChunkKey(key, dimensionId)) {"
)

start = s.index("    private static void applySubChunkLayers(")
end = s.index("\n    private static void decodeLegacySubChunk", start)
s = s[:start] + """    private static void applySubChunkLayers(int subChunkY, BlockLayer[] layers, TileBuilder builder) {
        int baseY = subChunkY * 16;
        for (int z = 0; z < 16; z++) {
            for (int x = 0; x < 16; x++) {
                int cell = z * 16 + x;
                if (baseY + 15 <= builder.surfaceY[cell]) continue;
                for (int y = 15; y >= 0; y--) {
                    int worldY = baseY + y;
                    if (worldY <= builder.surfaceY[cell]) break;
                    int index = (x << 8) | (z << 4) | y;
                    int visibleColor = 0;
                    for (int layer = layers.length - 1; layer >= 0; layer--) {
                        BlockLayer storage = layers[layer];
                        if (storage == null) continue;
                        visibleColor = storage.colorAt(index, x, z, worldY);
                        if (visibleColor != 0) break;
                    }
                    if (visibleColor != 0) {
                        builder.surfaceY[cell] = worldY;
                        builder.colors[cell] = visibleColor;
                        if (!builder.seen[cell]) { builder.seen[cell] = true; builder.surfaceCount++; }
                        break;
                    }
                }
            }
        }
    }
""" + s[end:]

old_start = s.index("    private static int blockColor(")
old_end = s.index("\n    private static int oreColor", old_start)
old = s[old_start:old_end]
body = old[old.index("        int color;"):old.index("        return texture(")]
s = s[:old_start] + """    private static int blockColor(String name, int x, int z, int y) {
        String n = name == null ? "" : name.toLowerCase(java.util.Locale.ROOT);
        return texture(blockBaseColor(n), x, z, y, n.hashCode());
    }

    private static int blockBaseColor(String n) {
""" + body + """        return color;
    }
""" + s[old_end:]

start = s.index("    private static final class BlockLayer {")
end = s.index("\n    private static final class PlayerPosition", start)
s = s[:start] + """    private static final class BlockLayer {
        final int bits, valuesPerWord;
        final int[] words;
        final int[] paletteColors;
        final int[] paletteSalts;
        final boolean[] paletteAir;
        BlockLayer(int bits, int valuesPerWord, int[] words, String[] palette) {
            this.bits = bits; this.valuesPerWord = valuesPerWord; this.words = words;
            this.paletteColors = new int[palette.length];
            this.paletteSalts = new int[palette.length];
            this.paletteAir = new boolean[palette.length];
            for (int i = 0; i < palette.length; i++) {
                String name = palette[i] == null ? "" : palette[i].toLowerCase(java.util.Locale.ROOT);
                paletteAir[i] = isAir(name);
                paletteColors[i] = blockBaseColor(name);
                paletteSalts[i] = name.hashCode();
            }
        }
        int colorAt(int index, int x, int z, int y) {
            int paletteIndex = 0;
            if (bits > 0) {
                int wordIndex = index / valuesPerWord;
                if (wordIndex >= words.length) return 0;
                int shift = (index % valuesPerWord) * bits;
                int mask = (1 << bits) - 1;
                paletteIndex = (words[wordIndex] >>> shift) & mask;
            }
            if (paletteIndex < 0 || paletteIndex >= paletteColors.length || paletteAir[paletteIndex]) return 0;
            return texture(paletteColors[paletteIndex], x, z, y, paletteSalts[paletteIndex]);
        }
    }
""" + s[end:]
engine.write_text(s)

view = Path("app/src/main/java/com/worldbridge/app/WorldPreviewView.java")
v = view.read_text()
v = v.replace("    private final int background = 0xFF294B88;", "    private final int background = 0xFF3B3B3B;")
v = v.replace("""        canvas.drawColor(background);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xFF274A86);
        canvas.drawRoundRect(dp(7), dp(7), getWidth() - dp(7), getHeight() - dp(7), dp(12), dp(12), paint);
""", """        canvas.drawColor(background);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xFF3B3B3B);
        canvas.drawRoundRect(dp(7), dp(7), getWidth() - dp(7), getHeight() - dp(7), dp(12), dp(12), paint);
""")
v = v.replace("        float chunkSize = scale;\n", "        float chunkSize = scale;\n        drawMissingChunkCheckerboard(canvas);\n")
v = v.replace("        drawSelection(canvas);\n", "        drawChunkGridAndLabels(canvas);\n        drawSelection(canvas);\n")
insert = v.index("    private void drawSelection(Canvas canvas)")
helpers = """    private void drawMissingChunkCheckerboard(Canvas canvas) {
        if (preview == null || scale < dp(2f)) return;
        int left = Math.max(preview.minChunkX, (int) Math.floor(-mapLeft / scale));
        int right = Math.min(preview.maxChunkX, (int) Math.ceil((getWidth() - mapLeft) / scale));
        int top = Math.max(preview.minChunkZ, (int) Math.floor(-mapTop / scale));
        int bottom = Math.min(preview.maxChunkZ, (int) Math.ceil((getHeight() - mapTop) / scale));
        long visible = Math.max(0L, (long) right - left + 1L) * Math.max(0L, (long) bottom - top + 1L);
        if (visible <= 0 || visible > 12000) return;
        paint.setStyle(Paint.Style.FILL);
        for (int cz = top; cz <= bottom; cz++) for (int cx = left; cx <= right; cx++) {
            long key = (((long) cx) << 32) | (cz & 0xFFFFFFFFL);
            if (preview.tiles.containsKey(key)) continue;
            paint.setColor(((cx ^ cz) & 1) == 0 ? 0xFF343434 : 0xFF414141);
            float l = mapLeft + cx * scale, t = mapTop + cz * scale;
            canvas.drawRect(l, t, l + scale + 0.4f, t + scale + 0.4f, paint);
        }
    }

    private void drawChunkGridAndLabels(Canvas canvas) {
        if (preview == null || scale < dp(7f)) return;
        int left = Math.max(preview.minChunkX, (int) Math.floor(-mapLeft / scale));
        int right = Math.min(preview.maxChunkX + 1, (int) Math.ceil((getWidth() - mapLeft) / scale));
        int top = Math.max(preview.minChunkZ, (int) Math.floor(-mapTop / scale));
        int bottom = Math.min(preview.maxChunkZ + 1, (int) Math.ceil((getHeight() - mapTop) / scale));
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(Math.max(0.5f, dp(0.65f)));
        paint.setColor(0x99D7D7D7);
        for (int cx = left; cx <= right; cx++) {
            float x = mapLeft + cx * scale;
            canvas.drawLine(x, mapTop + top * scale, x, mapTop + bottom * scale, paint);
        }
        for (int cz = top; cz <= bottom; cz++) {
            float y = mapTop + cz * scale;
            canvas.drawLine(mapLeft + left * scale, y, mapLeft + right * scale, y, paint);
        }
        paint.setStyle(Paint.Style.FILL);
        if (scale >= dp(25f)) {
            paint.setTextSize(dp(8f));
            paint.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
            paint.setColor(0xFFEAEAEA);
            for (int cz = top; cz < bottom; cz++) for (int cx = left; cx < right; cx++) {
                float x = mapLeft + cx * scale + dp(2f);
                float y = mapTop + cz * scale + dp(10f);
                if (x < getWidth() && y > 0 && y < getHeight())
                    canvas.drawText("(" + (cx * 16) + ", " + (cz * 16) + ")", x, y, paint);
            }
        }
    }

"""
v = v[:insert] + helpers + v[insert:]
view.write_text(v)
print("Optimized block map renderer applied")
