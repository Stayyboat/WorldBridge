from pathlib import Path

p = Path("engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java")
s = p.read_text()

# Bedrock has two historical version tags and several valid terrain-record
# tags. Do not require a Version record before recognising a saved column.
s = s.replace("import java.util.HashMap;", "import java.util.HashMap;\nimport java.util.HashSet;")
s = s.replace("import java.util.Map;", "import java.util.Map;\nimport java.util.Set;")

s = s.replace(
    "    private static final byte DATA_2D = 45;\n    private static final byte SUB_CHUNK_PREFIX = 47;\n    private static final byte LEGACY_VERSION = 118;",
    "    private static final byte DATA_2D = 45;\n    private static final byte DATA_2D_LEGACY = 46;\n    private static final byte SUB_CHUNK_PREFIX = 47;\n    private static final byte LEGACY_TERRAIN = 48;\n    private static final byte LEGACY_VERSION = 118;\n    private static final byte LEGACY_VERSION_2 = 119;"
)
assert "DATA_2D_LEGACY" in s and "LEGACY_VERSION_2" in s

start = s.index("            Map<Long, TileBuilder> builders = new HashMap<>();")
end = s.index("\n            // Keep the older biome/height preview", start)
replacement = """            Map<Long, TileBuilder> builders = new HashMap<>();
            List<Long> columns = new ArrayList<>();
            Set<Long> discoveredColumns = new HashSet<>();
            int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;

            // Recognise all terrain-bearing records, not only the column Version key.
            // This keeps older and partially saved Nether/End columns visible.
            try (DBIterator iterator = database.iterator(new ReadOptions().fillCache(false))) {
                while (iterator.hasNext()) {
                    java.util.Map.Entry<byte[], byte[]> record = iterator.next();
                    byte[] key = record.getKey();
                    if (!isSubChunkKey(key, dimensionId) && !isColumnTerrainKey(key, dimensionId)) continue;

                    int x = readIntLE(key, 0), z = readIntLE(key, 4);
                    long chunkKey = key(x, z);
                    TileBuilder builder = builders.computeIfAbsent(chunkKey, ignoredKey -> new TileBuilder(dimensionId));
                    if (discoveredColumns.add(chunkKey)) columns.add(chunkKey);
                    if (isColumnVersionKey(key, dimensionId)) builder.hasVersion = true;

                    minX = Math.min(minX, x); minZ = Math.min(minZ, z);
                    maxX = Math.max(maxX, x); maxZ = Math.max(maxZ, z);

                    if (isSubChunkKey(key, dimensionId)) {
                        int subChunkY = (byte) key[key.length - 1];
                        decodeSubChunk(record.getValue(), subChunkY, builder);
                    }
                }
            }
"""
s = s[:start] + replacement + s[end:]

# Include legacy Data2D data as a safe height fallback. makeTile handles its
# 4-byte per-column biome/RGB layout separately below.
s = s.replace(
    "                byte[] data2d = database.get(chunkKey(x, z, dimensionId, DATA_2D));\n                byte[] data3d = database.get(chunkKey(x, z, dimensionId, DATA_3D));\n                int[] coarsePixels = expandCoarseTile(makeTile(data2d, data3d, dimensionId));",
    """                byte[] data2d = database.get(chunkKey(x, z, dimensionId, DATA_2D));
                byte[] data2dLegacy = database.get(chunkKey(x, z, dimensionId, DATA_2D_LEGACY));
                byte[] data3d = database.get(chunkKey(x, z, dimensionId, DATA_3D));
                byte[] heightSource = data2d != null ? data2d : data2dLegacy;
                int[] coarsePixels = expandCoarseTile(makeTile(heightSource, data3d, dimensionId));"""
)
s = s.replace(
    "                if ((data2d != null && data2d.length >= 512) || (data3d != null && data3d.length >= 512)) {",
    "                if ((data2d != null && data2d.length >= 512) || (data2dLegacy != null && data2dLegacy.length >= 512) || (data3d != null && data3d.length >= 512)) {"
)

# Replace the narrow Version-only detector with dimension-aware terrain-key parsing.
old = """    private static boolean isColumnVersionKey(byte[] key, int dimensionId) {
        int expected = dimensionId == 0 ? 9 : 13;
        if (key.length != expected) return false;
        int type = key[key.length - 1] & 0xFF;
        return type == (VERSION & 0xFF) || type == (LEGACY_VERSION & 0xFF);
    }

    private static boolean isSubChunkKey(byte[] key, int dimensionId) {
        int expected = dimensionId == 0 ? 10 : 14;
        return key.length == expected && (key[key.length - 2] & 0xFF) == (SUB_CHUNK_PREFIX & 0xFF);
    }
"""
new = """    private static int columnKeyLength(int dimensionId) {
        return dimensionId == 0 ? 9 : 13;
    }

    private static boolean isColumnVersionKey(byte[] key, int dimensionId) {
        if (key.length != columnKeyLength(dimensionId)) return false;
        if (dimensionId != 0 && readIntLE(key, 8) != dimensionId) return false;
        int type = key[key.length - 1] & 0xFF;
        return type == (VERSION & 0xFF) || type == (LEGACY_VERSION & 0xFF)
                || type == (LEGACY_VERSION_2 & 0xFF);
    }

    private static boolean isColumnTerrainKey(byte[] key, int dimensionId) {
        if (key.length != columnKeyLength(dimensionId)) return false;
        if (dimensionId != 0 && readIntLE(key, 8) != dimensionId) return false;
        int type = key[key.length - 1] & 0xFF;
        return type == (DATA_3D & 0xFF) || type == (VERSION & 0xFF)
                || type == (DATA_2D & 0xFF) || type == (DATA_2D_LEGACY & 0xFF)
                || type == (LEGACY_TERRAIN & 0xFF) || type == (LEGACY_VERSION & 0xFF)
                || type == (LEGACY_VERSION_2 & 0xFF);
    }

    private static boolean isSubChunkKey(byte[] key, int dimensionId) {
        int expected = columnKeyLength(dimensionId) + 1;
        return key.length == expected
                && (dimensionId == 0 || readIntLE(key, 8) == dimensionId)
                && (key[key.length - 2] & 0xFF) == (SUB_CHUNK_PREFIX & 0xFF);
    }
"""
assert old in s
s = s.replace(old, new)

# Nether surface extraction must look up from the playable floor, skipping bedrock.
start = s.index("    private static void applySubChunkLayers(")
end = s.index("\n    private static void decodeLegacySubChunk", start)
apply_method = """    private static void applySubChunkLayers(int subChunkY, BlockLayer[] layers, TileBuilder builder) {
        int baseY = subChunkY * 16;
        boolean floorView = builder.floorSurface;
        for (int z = 0; z < 16; z++) {
            for (int x = 0; x < 16; x++) {
                int cell = z * 16 + x;
                if (!floorView && baseY + 15 <= builder.surfaceY[cell]) continue;
                if (floorView && baseY >= builder.surfaceY[cell]) continue;

                int firstY = floorView ? 0 : 15;
                int endY = floorView ? 16 : -1;
                int step = floorView ? 1 : -1;
                for (int y = firstY; y != endY; y += step) {
                    int worldY = baseY + y;
                    if ((!floorView && worldY <= builder.surfaceY[cell])
                            || (floorView && worldY >= builder.surfaceY[cell])) break;
                    int index = (x << 8) | (z << 4) | y;
                    int visibleColor = 0;
                    for (int layer = layers.length - 1; layer >= 0; layer--) {
                        BlockLayer storage = layers[layer];
                        if (storage == null) continue;
                        visibleColor = storage.colorAt(index, x, z, worldY, floorView);
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
"""
s = s[:start] + apply_method + s[end:]

# Legacy subchunks follow the same per-dimension surface direction.
start = s.index("    private static void decodeLegacySubChunk(")
end = s.index("\n    private static String readBlockPaletteName", start)
legacy_method = """    private static void decodeLegacySubChunk(ByteBuffer in, int subChunkY, TileBuilder builder) {
        if (in.remaining() < 4096 + 2048) return;
        byte[] ids = new byte[4096]; in.get(ids);
        byte[] meta = new byte[2048]; in.get(meta);
        for (int z = 0; z < 16; z++) for (int x = 0; x < 16; x++) {
            int cell = z * 16 + x;
            int firstY = builder.floorSurface ? 0 : 15;
            int endY = builder.floorSurface ? 16 : -1;
            int step = builder.floorSurface ? 1 : -1;
            for (int y = firstY; y != endY; y += step) {
                int index = (x << 8) | (z << 4) | y;
                int id = ids[index] & 0xFF;
                if (id == 0 || (builder.floorSurface && id == 7)) continue;
                int data = ((meta[index >>> 1] & 0xFF) >>> ((index & 1) * 4)) & 15;
                int worldY = subChunkY * 16 + y;
                boolean better = builder.floorSurface
                        ? worldY < builder.surfaceY[cell] : worldY > builder.surfaceY[cell];
                if (better) {
                    builder.surfaceY[cell] = worldY;
                    builder.colors[cell] = legacyBlockColor(id, data, x, z, worldY);
                    if (!builder.seen[cell]) { builder.seen[cell] = true; builder.surfaceCount++; }
                }
                break;
            }
        }
    }
"""
s = s[:start] + legacy_method + s[end:]

# Expand block palette cache with a bedrock flag used by the Nether floor view.
s = s.replace(
    "        final boolean[] paletteAir;\n",
    "        final boolean[] paletteAir;\n        final boolean[] paletteBedrock;\n"
)
s = s.replace(
    "            this.paletteAir = new boolean[palette.length];\n",
    "            this.paletteAir = new boolean[palette.length];\n            this.paletteBedrock = new boolean[palette.length];\n"
)
s = s.replace(
    "                paletteAir[i] = isAir(name);\n",
    "                paletteAir[i] = isAir(name);\n                paletteBedrock[i] = name.endsWith(\":bedrock\");\n"
)
old = """        int colorAt(int index, int x, int z, int y) {
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
"""
new = """        int colorAt(int index, int x, int z, int y, boolean ignoreBedrock) {
            int paletteIndex = 0;
            if (bits > 0) {
                int wordIndex = index / valuesPerWord;
                if (wordIndex >= words.length) return 0;
                int shift = (index % valuesPerWord) * bits;
                int mask = (1 << bits) - 1;
                paletteIndex = (words[wordIndex] >>> shift) & mask;
            }
            if (paletteIndex < 0 || paletteIndex >= paletteColors.length || paletteAir[paletteIndex]
                    || (ignoreBedrock && paletteBedrock[paletteIndex])) return 0;
            return texture(paletteColors[paletteIndex], x, z, y, paletteSalts[paletteIndex]);
        }
"""
assert old in s
s = s.replace(old, new)

# Give Nether and End their own terrain palette treatment.
s = s.replace(
    '        else if (n.contains("sandstone") || n.contains("sand")) color = 0xFFD7C17A;\n',
    '        else if (n.contains("end_stone")) color = 0xFFD9D08C;\n        else if (n.contains("sandstone") || n.contains("sand")) color = 0xFFD7C17A;\n'
)
s = s.replace(
    '        else if (n.contains("obsidian")) color = 0xFF38304D;\n',
    '        else if (n.contains("obsidian")) color = 0xFF38304D;\n        else if (n.contains("purpur")) color = 0xFFAA82B5;\n        else if (n.contains("chorus")) color = 0xFF795A91;\n        else if (n.contains("end_rod")) color = 0xFFD9DCE0;\n        else if (n.contains("end_portal")) color = 0xFF27233F;\n        else if (n.contains("shroomlight") || n.contains("glowstone")) color = 0xFFE5B56B;\n'
)

# Tile builders store their surface direction and initialise the correct extreme.
old = """    private static final class TileBuilder {
        final int[] colors = new int[256];
        final int[] surfaceY = new int[256];
        final boolean[] seen = new boolean[256];
        int surfaceCount;
        boolean hasVersion;
        TileBuilder() { Arrays.fill(surfaceY, Integer.MIN_VALUE); }
    }
"""
new = """    private static final class TileBuilder {
        final int[] colors = new int[256];
        final int[] surfaceY = new int[256];
        final boolean[] seen = new boolean[256];
        final boolean floorSurface;
        int surfaceCount;
        boolean hasVersion;
        TileBuilder(int dimensionId) {
            floorSurface = dimensionId == 1;
            Arrays.fill(surfaceY, floorSurface ? Integer.MAX_VALUE : Integer.MIN_VALUE);
        }
    }
"""
assert old in s
s = s.replace(old, new)

# Data2DLegacy stores biome ID plus RGB in four-byte cells; sample the ID byte only.
old = """        if (data3d == null && data2d != null && data2d.length >= 768) {
            ByteBuffer b = ByteBuffer.wrap(data2d).order(ByteOrder.LITTLE_ENDIAN); b.position(512);
            for (int i = 0; i < 256; i++) biomes[i] = b.get() & 255;
        } else Arrays.fill(biomes, dimensionId == 1 ? 8 : dimensionId == 2 ? 9 : 1);
"""
new = """        if (data3d == null && data2d != null && data2d.length >= 1536) {
            ByteBuffer b = ByteBuffer.wrap(data2d).order(ByteOrder.LITTLE_ENDIAN); b.position(512);
            for (int i = 0; i < 256; i++) { biomes[i] = b.get() & 255; b.position(b.position() + 3); }
        } else if (data3d == null && data2d != null && data2d.length >= 768) {
            ByteBuffer b = ByteBuffer.wrap(data2d).order(ByteOrder.LITTLE_ENDIAN); b.position(512);
            for (int i = 0; i < 256; i++) biomes[i] = b.get() & 255;
        } else Arrays.fill(biomes, dimensionId == 1 ? 8 : dimensionId == 2 ? 9 : 1);
"""
assert old in s
s = s.replace(old, new)

p.write_text(s)
print("Added multi-record dimension discovery, legacy version support, Nether floor surfaces and End palette colours.")
