from pathlib import Path

engine = Path('engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java')
s = engine.read_text()

old = '''    public static PreviewData scan(File worldDirectory, int dimensionId) throws IOException {
        if (worldDirectory == null || !new File(worldDirectory, "level.dat").isFile()'''
new = '''    public static PreviewData scan(File worldDirectory, int dimensionId) throws IOException {
        return scan(worldDirectory, dimensionId, null);
    }

    public interface ProgressListener {
        void onProgress(PreviewData partial, int columnsSeen);
    }

    public static PreviewData scan(File worldDirectory, int dimensionId, ProgressListener progressListener) throws IOException {
        if (worldDirectory == null || !new File(worldDirectory, "level.dat").isFile()'''
assert old in s
s = s.replace(old, new, 1)

old = '''            List<Long> columns = new ArrayList<>();
            Set<Long> discoveredColumns = new HashSet<>();
            int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;'''
new = '''            List<Long> columns = new ArrayList<>();
            Set<Long> discoveredColumns = new HashSet<>();
            Map<Long, byte[]> data2dRecords = new HashMap<>();
            Map<Long, byte[]> data2dLegacyRecords = new HashMap<>();
            Map<Long, byte[]> data3dRecords = new HashMap<>();
            int nextProgressAt = 128;
            int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;'''
assert old in s
s = s.replace(old, new, 1)

old = '''                while (iterator.hasNext()) {
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
                }'''
new = '''                while (iterator.hasNext()) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                    java.util.Map.Entry<byte[], byte[]> record = iterator.next();
                    byte[] key = record.getKey();
                    boolean subChunkRecord = isSubChunkKey(key, dimensionId);
                    boolean columnRecord = isColumnTerrainKey(key, dimensionId);
                    if (!subChunkRecord && !columnRecord) continue;

                    int x = readIntLE(key, 0), z = readIntLE(key, 4);
                    long chunkKey = key(x, z);
                    TileBuilder builder = builders.computeIfAbsent(chunkKey, ignoredKey -> new TileBuilder(dimensionId));
                    if (discoveredColumns.add(chunkKey)) {
                        columns.add(chunkKey);
                        if (progressListener != null && columns.size() >= nextProgressAt) {
                            PreviewData partial = createCoveragePreview(builders, minX, maxX, minZ, maxZ, dimensionId);
                            progressListener.onProgress(partial, columns.size());
                            nextProgressAt = Integer.MAX_VALUE;
                        }
                    }
                    if (isColumnVersionKey(key, dimensionId)) builder.hasVersion = true;

                    minX = Math.min(minX, x); minZ = Math.min(minZ, z);
                    maxX = Math.max(maxX, x); maxZ = Math.max(maxZ, z);

                    if (columnRecord) {
                        byte type = key[key.length - 1];
                        byte[] value = record.getValue();
                        if (type == DATA_2D) data2dRecords.put(chunkKey, value);
                        else if (type == DATA_2D_LEGACY) data2dLegacyRecords.put(chunkKey, value);
                        else if (type == DATA_3D) data3dRecords.put(chunkKey, value);
                    }
                    if (subChunkRecord) {
                        int subChunkY = (byte) key[key.length - 1];
                        decodeSubChunk(record.getValue(), subChunkY, builder);
                    }
                }'''
assert old in s
s = s.replace(old, new, 1)

old = '''            // Keep the older biome/height preview as a fallback for legacy or unreadable palettes.
            Map<Long, int[]> tiles = new HashMap<>(Math.max(16, columns.size() * 4 / 3));'''
new = '''            if (progressListener != null && !columns.isEmpty() && columns.size() < 128) {
                progressListener.onProgress(createCoveragePreview(builders, minX, maxX, minZ, maxZ, dimensionId), columns.size());
            }

            // Keep the older biome/height preview as a fallback for legacy or unreadable palettes.
            Map<Long, int[]> tiles = new HashMap<>(Math.max(16, columns.size() * 4 / 3));'''
assert old in s
s = s.replace(old, new, 1)

old = '''                int[] pixels;
                byte[] data2d = database.get(chunkKey(x, z, dimensionId, DATA_2D));
                byte[] data2dLegacy = database.get(chunkKey(x, z, dimensionId, DATA_2D_LEGACY));
                byte[] data3d = database.get(chunkKey(x, z, dimensionId, DATA_3D));'''
new = '''                if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                int[] pixels;
                byte[] data2d = data2dRecords.get(chunkKey);
                byte[] data2dLegacy = data2dLegacyRecords.get(chunkKey);
                byte[] data3d = data3dRecords.get(chunkKey);'''
assert old in s
s = s.replace(old, new, 1)

insert_at = s.index('    private static int columnKeyLength(')
helper = '''    private static PreviewData createCoveragePreview(Map<Long, TileBuilder> builders,
            int minX, int maxX, int minZ, int maxZ, int dimensionId) {
        Map<Long, int[]> tiles = new HashMap<>(Math.max(16, builders.size() * 4 / 3));
        int fallback = dimensionId == 1 ? 0xFF914D3E : dimensionId == 2 ? 0xFF9581B2 : 0xFF46576A;
        for (Map.Entry<Long, TileBuilder> entry : builders.entrySet()) {
            TileBuilder builder = entry.getValue();
            int[] colors = builder.colors.clone();
            if (builder.surfaceCount == 0) Arrays.fill(colors, fallback);
            else for (int i = 0; i < colors.length; i++) if (!builder.seen[i]) colors[i] = fallback;
            tiles.put(entry.getKey(), colors);
        }
        int actualMinX = Integer.MAX_VALUE, actualMinZ = Integer.MAX_VALUE;
        int actualMaxX = Integer.MIN_VALUE, actualMaxZ = Integer.MIN_VALUE;
        for (long key : tiles.keySet()) {
            int x = (int) (key >> 32), z = (int) key;
            actualMinX = Math.min(actualMinX, x); actualMinZ = Math.min(actualMinZ, z);
            actualMaxX = Math.max(actualMaxX, x); actualMaxZ = Math.max(actualMaxZ, z);
        }
        return new PreviewData(tiles, actualMinX, actualMaxX, actualMinZ, actualMaxZ, dimensionId, false, false, null);
    }

'''
s = s[:insert_at] + helper + s[insert_at:]

old = '''        public int getChunkCount() { return tiles.size(); }
    }
}'''
new = '''        public int getChunkCount() { return tiles.size(); }

        public PreviewData withoutRegion(int minChunkX, int minChunkZ, int maxChunkX, int maxChunkZ) {
            Map<Long, int[]> remaining = new HashMap<>(Math.max(16, tiles.size()));
            int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
            for (Map.Entry<Long, int[]> entry : tiles.entrySet()) {
                int x = (int) (entry.getKey() >> 32), z = (int) (long) entry.getKey();
                if (x >= minChunkX && x <= maxChunkX && z >= minChunkZ && z <= maxChunkZ) continue;
                remaining.put(entry.getKey(), entry.getValue());
                minX = Math.min(minX, x); minZ = Math.min(minZ, z);
                maxX = Math.max(maxX, x); maxZ = Math.max(maxZ, z);
            }
            if (remaining.isEmpty()) return new PreviewData(remaining, 0, -1, 0, -1,
                    dimensionId, hasBiomeOrHeightData, hasBlockData, null);
            PlayerPosition player = hasPlayerPosition
                    ? new PlayerPosition(playerX, 0, playerZ, playerYaw, playerDimensionId) : null;
            return new PreviewData(remaining, minX, maxX, minZ, maxZ,
                    dimensionId, hasBiomeOrHeightData, hasBlockData, player);
        }
    }
}'''
assert old in s
s = s.replace(old, new, 1)
engine.write_text(s)

activity = Path('app/src/main/java/com/worldbridge/app/MainActivity.java')
a = activity.read_text()
a = a.replace('import java.util.concurrent.Executors;', '''import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;''')
a = a.replace('''    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private File workspace;''', '''    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ExecutorService previewWorker = Executors.newSingleThreadExecutor();
    private final Object worldDbLock = new Object();
    private final Map<Integer, BedrockWorldPreview.PreviewData> previewCache = new ConcurrentHashMap<>();
    private Future<?> previewTask;
    private Future<?> prefetchTask;
    private File workspace;''')

a = a.replace('''    private void importWorld(Uri uri) {
        setBusy(true, "Importing the world and preparing a protected copy…");''', '''    private void importWorld(Uri uri) {
        cancelPreviewWork();
        previewCache.clear();
        setBusy(true, "Importing the world and preparing a protected copy…");''')

import_start = a.index("    private void importWorld(Uri uri) {")
lambda_open = a.index("        worker.execute(() -> {", import_start)
body_start = lambda_open + len("        worker.execute(() -> {\n")
lambda_close = a.index("        });\n    }\n\n    private void reviewAndPrune()", body_start)
body = a[body_start:lambda_close]
a = a[:body_start] + "            synchronized (worldDbLock) {\n" + body + "\n            }\n" + a[lambda_close:]

a = a.replace('''                    worldLoaded = true;
                    lastExportUri = null;''', '''                    worldLoaded = true;
                    previewCache.clear();
                    lastExportUri = null;''', 1)

a = a.replace('''    private void pruneSelected(int dimensionIndex) {
        final int minX''', '''    private void pruneSelected(int dimensionIndex) {
        cancelPreviewWork();
        final int minX''')

old = '''                BedrockChunkPruner.Result result = BedrockChunkPruner.prune(
                        workingWorld, dimensionId, minX, minZ, maxX, maxZ, scratch
                );
                runOnUiThread(() -> {'''
new = '''                BedrockChunkPruner.Result result;
                synchronized (worldDbLock) {
                    result = BedrockChunkPruner.prune(
                            workingWorld, dimensionId, minX, minZ, maxX, maxZ, scratch
                    );
                    if (result.recordsDeleted > 0) {
                        BedrockWorldPreview.PreviewData cached = previewCache.get(dimensionId);
                        if (cached != null) previewCache.put(dimensionId, cached.withoutRegion(minX, minZ, maxX, maxZ));
                    }
                }
                runOnUiThread(() -> {'''
assert old in a
a = a.replace(old, new, 1)

a = a.replace('''    private void resetWorkingCopy() {
        setBusy(true, "Restoring the original working copy…");''', '''    private void resetWorkingCopy() {
        cancelPreviewWork();
        previewCache.clear();
        setBusy(true, "Restoring the original working copy…");''')
a = a.replace('''                WorldFiles.copyDirectory(originalWorld, workingWorld);''', '''                synchronized (worldDbLock) {
                    WorldFiles.copyDirectory(originalWorld, workingWorld);
                    previewCache.clear();
                }''', 1)

start = a.index('    private void loadWorldPreview() {')
end = a.index('\n    private String getDisplayName(', start)
new_loader = '''    private void cancelPreviewWork() {
        previewRequestId++;
        Future<?> task = previewTask;
        Future<?> warmup = prefetchTask;
        previewTask = null;
        prefetchTask = null;
        if (task != null) task.cancel(true);
        if (warmup != null) warmup.cancel(true);
    }

    private void loadWorldPreview() {
        if (!worldLoaded || mapView == null) return;
        final int requestId = ++previewRequestId;
        final int dimensionId = dimensionSpinner.getSelectedItemPosition();
        Future<?> previous = previewTask;
        Future<?> warmup = prefetchTask;
        prefetchTask = null;
        if (previous != null) previous.cancel(true);
        if (warmup != null) warmup.cancel(true);

        BedrockWorldPreview.PreviewData cached = previewCache.get(dimensionId);
        if (cached != null) {
            previewStatus.setText("Showing cached preview…");
            previewTask = previewWorker.submit(() -> {
                try { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DEFAULT); } catch (Exception ignored) { }
                Bitmap overview = WorldPreviewView.createOverviewBitmap(cached);
                runOnUiThread(() -> {
                    if (requestId != previewRequestId || !worldLoaded) {
                        if (overview != null && !overview.isRecycled()) overview.recycle();
                        return;
                    }
                    mapView.setPreview(cached, overview);
                    mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                    updatePreviewStatus(cached);
                    prefetchOtherDimensions(dimensionId);
                });
            });
            return;
        }

        previewStatus.setText("Scanning chunks… the map will appear while details load.");
        previewTask = previewWorker.submit(() -> {
            try {
                try { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DEFAULT); } catch (Exception ignored) { }
                BedrockWorldPreview.PreviewData data;
                synchronized (worldDbLock) {
                    data = BedrockWorldPreview.scan(workingWorld, dimensionId, (partial, columnsSeen) -> {
                        if (Thread.currentThread().isInterrupted()) return;
                        Bitmap partialOverview = WorldPreviewView.createOverviewBitmap(partial);
                        runOnUiThread(() -> {
                            if (requestId != previewRequestId || !worldLoaded) {
                                if (partialOverview != null && !partialOverview.isRecycled()) partialOverview.recycle();
                                return;
                            }
                            mapView.setPreview(partial, partialOverview);
                            mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                            previewStatus.setText(String.format("Found %,d chunk columns · loading terrain detail…", columnsSeen));
                        });
                    });
                    if (Thread.currentThread().isInterrupted()) return;
                    cachePreviewData(dimensionId, data);
                }
                if (Thread.currentThread().isInterrupted()) return;
                Bitmap overview = WorldPreviewView.createOverviewBitmap(data);
                runOnUiThread(() -> {
                    if (requestId != previewRequestId || !worldLoaded) {
                        if (overview != null && !overview.isRecycled()) overview.recycle();
                        return;
                    }
                    mapView.setPreview(data, overview);
                    mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                    updatePreviewStatus(data);
                    prefetchOtherDimensions(dimensionId);
                });
            } catch (Exception exception) {
                if (Thread.currentThread().isInterrupted()) return;
                runOnUiThread(() -> {
                    if (requestId != previewRequestId) return;
                    previewStatus.setText("Map preview unavailable: " + friendlyMessage(exception));
                    mapView.setPreview(null, null);
                });
            }
        });
    }

    private void prefetchOtherDimensions(int activeDimension) {
        if (!worldLoaded || busy) return;
        Future<?> previous = prefetchTask;
        if (previous != null) previous.cancel(true);
        prefetchTask = previewWorker.submit(() -> {
            try {
                android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
            } catch (Exception ignored) { }
            for (int dimension = 0; dimension < 3; dimension++) {
                if (dimension == activeDimension || Thread.currentThread().isInterrupted()) continue;
                if (previewCache.containsKey(dimension)) continue;
                try {
                    BedrockWorldPreview.PreviewData data;
                    synchronized (worldDbLock) {
                        data = BedrockWorldPreview.scan(workingWorld, dimension);
                        if (Thread.currentThread().isInterrupted() || !worldLoaded) return;
                        cachePreviewData(dimension, data);
                    }
                    if (Thread.currentThread().isInterrupted() || !worldLoaded) return;
                } catch (Exception exception) {
                    if (Thread.currentThread().isInterrupted()) return;
                }
            }
        });
    }

    private void cachePreviewData(int dimensionId, BedrockWorldPreview.PreviewData data) {
        previewCache.put(dimensionId, data);
        int totalChunks = 0;
        for (BedrockWorldPreview.PreviewData cached : previewCache.values()) totalChunks += cached.getChunkCount();
        if (totalChunks > 30000) {
            previewCache.clear();
            previewCache.put(dimensionId, data);
        }
    }

    private void updatePreviewStatus(BedrockWorldPreview.PreviewData data) {
        if (data.getChunkCount() == 0) {
            previewStatus.setText("No saved chunk columns were found in this dimension.");
        } else if (data.hasBiomeOrHeightData) {
            previewStatus.setText(String.format("%,d saved chunk columns · stored biome/height data · approximate terrain colours · drag to select", data.getChunkCount()));
        } else {
            previewStatus.setText(String.format("%,d saved chunk columns · showing block terrain and chunk coverage", data.getChunkCount()));
        }
    }
'''
a = a[:start] + new_loader + a[end:]

a = a.replace('''    protected void onDestroy() {
        super.onDestroy();
        worker.shutdown();
    }''', '''    protected void onDestroy() {
        cancelPreviewWork();
        super.onDestroy();
        previewWorker.shutdownNow();
        worker.shutdown();
    }''')
activity.write_text(a)
print('Applied faster preview lifecycle.')



# Replace the one-pass/first-128 preview with a complete-footprint-first pipeline.
# Pass one only discovers chunk coordinates. Pass two decodes saved terrain palettes
# and progressively replaces neutral coverage tiles with actual terrain colours.
engine = Path('engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java')
s = engine.read_text()
scan_start = s.index('            Map<Long, TileBuilder> builders = new HashMap<>();',
    s.index('public static PreviewData scan(File worldDirectory, int dimensionId, ProgressListener'))
scan_end = s.index('\n            // Keep the older biome/height preview as a fallback', scan_start)
new_scan = r'''            List<Long> columns = new ArrayList<>();
            Set<Long> discoveredColumns = new HashSet<>();
            int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;

            // Pass 1: discover the complete chunk footprint without decoding block palettes.
            // This avoids showing only the first 128 LevelDB keys, which can look like thin stripes.
            try (DBIterator iterator = database.iterator(new ReadOptions().fillCache(false))) {
                while (iterator.hasNext()) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                    java.util.Map.Entry<byte[], byte[]> record = iterator.next();
                    byte[] key = record.getKey();
                    if (!isSubChunkKey(key, dimensionId) && !isColumnTerrainKey(key, dimensionId)) continue;
                    int x = readIntLE(key, 0), z = readIntLE(key, 4);
                    long chunkKey = key(x, z);
                    if (discoveredColumns.add(chunkKey)) columns.add(chunkKey);
                    minX = Math.min(minX, x); minZ = Math.min(minZ, z);
                    maxX = Math.max(maxX, x); maxZ = Math.max(maxZ, z);
                }
            }

            if (columns.isEmpty()) {
                PlayerPosition player = readPlayerPosition(database.get(LOCAL_PLAYER));
                if (database != null) { database.close(); database = null; }
                return new PreviewData(new HashMap<>(), 0, -1, 0, -1, dimensionId, false, false, player);
            }

            // Publish every discovered chunk column immediately. Terrain detail is filled in below.
            if (progressListener != null) {
                int fallback = dimensionId == 1 ? 0xFF914D3E : dimensionId == 2 ? 0xFF9581B2 : 0xFF607080;
                int[] fallbackTile = new int[256];
                Arrays.fill(fallbackTile, fallback);
                Map<Long, int[]> coverageTiles = new HashMap<>(Math.max(16, columns.size() * 4 / 3));
                for (long chunkKey : columns) coverageTiles.put(chunkKey, fallbackTile);
                progressListener.onProgress(new PreviewData(coverageTiles, minX, maxX, minZ, maxZ,
                        dimensionId, false, false, null), columns.size());
            }

            // Pass 2: decode actual block terrain while keeping all columns in partial snapshots.
            Map<Long, TileBuilder> builders = new HashMap<>(Math.max(16, columns.size() * 4 / 3));
            Map<Long, byte[]> data2dRecords = new HashMap<>();
            Map<Long, byte[]> data2dLegacyRecords = new HashMap<>();
            Map<Long, byte[]> data3dRecords = new HashMap<>();
            Set<Long> detailedColumns = new HashSet<>();
            int nextProgressAt = 128;
            try (DBIterator iterator = database.iterator(new ReadOptions().fillCache(false))) {
                while (iterator.hasNext()) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                    java.util.Map.Entry<byte[], byte[]> record = iterator.next();
                    byte[] key = record.getKey();
                    boolean subChunkRecord = isSubChunkKey(key, dimensionId);
                    boolean columnRecord = isColumnTerrainKey(key, dimensionId);
                    if (!subChunkRecord && !columnRecord) continue;

                    int x = readIntLE(key, 0), z = readIntLE(key, 4);
                    long chunkKey = key(x, z);
                    TileBuilder builder = builders.computeIfAbsent(chunkKey, ignoredKey -> new TileBuilder(dimensionId));
                    if (isColumnVersionKey(key, dimensionId)) builder.hasVersion = true;

                    if (columnRecord) {
                        byte type = key[key.length - 1];
                        byte[] value = record.getValue();
                        if (type == DATA_2D) data2dRecords.put(chunkKey, value);
                        else if (type == DATA_2D_LEGACY) data2dLegacyRecords.put(chunkKey, value);
                        else if (type == DATA_3D) data3dRecords.put(chunkKey, value);
                    }
                    if (subChunkRecord) {
                        int subChunkY = (byte) key[key.length - 1];
                        decodeSubChunk(record.getValue(), subChunkY, builder);
                        if (progressListener != null && detailedColumns.add(chunkKey)
                                && detailedColumns.size() >= nextProgressAt) {
                            PreviewData partial = createCoveragePreview(columns, builders,
                                    minX, maxX, minZ, maxZ, dimensionId);
                            progressListener.onProgress(partial, columns.size());
                            nextProgressAt = Math.max(nextProgressAt + 1, nextProgressAt * 2);
                        }
                    }
                }
            }
'''
s = s[:scan_start] + new_scan + s[scan_end:]

helper_start = s.index('    private static PreviewData createCoveragePreview(')
helper_end = s.index('\n    private static int columnKeyLength(', helper_start)
new_helper = r'''    private static PreviewData createCoveragePreview(List<Long> columns, Map<Long, TileBuilder> builders,
            int minX, int maxX, int minZ, int maxZ, int dimensionId) {
        Map<Long, int[]> tiles = new HashMap<>(Math.max(16, columns.size() * 4 / 3));
        int fallback = dimensionId == 1 ? 0xFF914D3E : dimensionId == 2 ? 0xFF9581B2 : 0xFF607080;
        int[] fallbackTile = new int[256];
        Arrays.fill(fallbackTile, fallback);
        for (long chunkKey : columns) {
            TileBuilder builder = builders.get(chunkKey);
            if (builder == null || builder.surfaceCount == 0) {
                tiles.put(chunkKey, fallbackTile);
            } else {
                int[] colors = builder.colors.clone();
                for (int i = 0; i < colors.length; i++) if (!builder.seen[i]) colors[i] = fallback;
                tiles.put(chunkKey, colors);
            }
        }
        return new PreviewData(tiles, minX, maxX, minZ, maxZ, dimensionId, false, false, null);
    }
'''
s = s[:helper_start] + new_helper + s[helper_end:]
engine.write_text(s)

# Make the status describe the full coverage map while terrain detail is being filled in.
activity = Path('app/src/main/java/com/worldbridge/app/MainActivity.java')
a = activity.read_text()
a = a.replace('Found %,d chunk columns · loading terrain detail…',
              'Found %,d chunk columns · full map coverage · filling terrain detail…')
activity.write_text(a)
print('Applied full-footprint-first preview pipeline.')
