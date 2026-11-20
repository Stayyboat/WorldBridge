from pathlib import Path

engine = Path('engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java')
s = engine.read_text()
start = s.index('    public static PreviewData scan(File worldDirectory, int dimensionId) throws IOException {')
end = s.index('    private static int columnKeyLength(', start)
new = r'''    public static PreviewData scan(File worldDirectory, int dimensionId) throws IOException {
        return scanAll(worldDirectory, dimensionId, null).get(dimensionId);
    }

    public interface ProgressListener {
        /** The current scanner uses null for lightweight progress updates. */
        void onProgress(PreviewData partial, int columnsSeen);
    }

    public static PreviewData scan(File worldDirectory, int dimensionId, ProgressListener progressListener) throws IOException {
        return scanAll(worldDirectory, dimensionId, progressListener).get(dimensionId);
    }

    /** One LevelDB walk discovers all dimensions; only the selected dimension decodes block palettes. */
    public static Map<Integer, PreviewData> scanAll(File worldDirectory, int detailedDimension,
            ProgressListener progressListener) throws IOException {
        if (worldDirectory == null || !new File(worldDirectory, "level.dat").isFile()
                || !new File(worldDirectory, "db").isDirectory()) {
            throw new IOException("The selected folder is not a Bedrock world.");
        }
        if (detailedDimension < 0 || detailedDimension > 2) throw new IOException("Unsupported dimension.");

        Options options = new Options().createIfMissing(false)
                .compressionType(CompressionType.ZLIB_RAW)
                .cacheSize(16L * 1024L * 1024L).writeBufferSize(1024 * 1024);
        DB database = null;
        try {
            DBFactory factory = new Iq80DBFactory();
            database = factory.open(new File(worldDirectory, "db"), options);
            DimensionScanState[] states = new DimensionScanState[]{
                    new DimensionScanState(), new DimensionScanState(), new DimensionScanState()
            };
            long recordsVisited = 0;
            int totalColumns = 0;

            try (DBIterator iterator = database.iterator(new ReadOptions().fillCache(true))) {
                while (iterator.hasNext()) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                    java.util.Map.Entry<byte[], byte[]> record = iterator.next();
                    recordsVisited++;
                    byte[] key = record.getKey();
                    int dimensionId = dimensionForRecord(key);
                    if (dimensionId < 0) {
                        if (progressListener != null && recordsVisited % 50000L == 0L) {
                            progressListener.onProgress(null, totalColumns);
                        }
                        continue;
                    }

                    boolean subChunkRecord = isSubChunkKey(key, dimensionId);
                    boolean columnRecord = isColumnTerrainKey(key, dimensionId);
                    if (!subChunkRecord && !columnRecord) continue;

                    int x = readIntLE(key, 0), z = readIntLE(key, 4);
                    long chunkKey = key(x, z);
                    DimensionScanState state = states[dimensionId];
                    if (state.discoveredColumns.add(chunkKey)) {
                        state.columns.add(chunkKey);
                        state.minX = Math.min(state.minX, x);
                        state.minZ = Math.min(state.minZ, z);
                        state.maxX = Math.max(state.maxX, x);
                        state.maxZ = Math.max(state.maxZ, z);
                        totalColumns++;
                    }

                    if (columnRecord) {
                        byte type = key[key.length - 1];
                        byte[] value = record.getValue();
                        if (type == DATA_2D) state.data2dRecords.put(chunkKey, value);
                        else if (type == DATA_2D_LEGACY) state.data2dLegacyRecords.put(chunkKey, value);
                        else if (type == DATA_3D) state.data3dRecords.put(chunkKey, value);
                    }

                    // Other dimensions get instant coarse maps. Their block palettes are decoded on first visit.
                    if (dimensionId == detailedDimension && subChunkRecord) {
                        TileBuilder builder = state.builders.computeIfAbsent(chunkKey,
                                ignoredKey -> new TileBuilder(detailedDimension));
                        int subChunkY = (byte) key[key.length - 1];
                        decodeSubChunk(record.getValue(), subChunkY, builder);
                    }

                    if (progressListener != null && recordsVisited % 50000L == 0L) {
                        progressListener.onProgress(null, totalColumns);
                    }
                }
            }

            PlayerPosition player = readPlayerPosition(database.get(LOCAL_PLAYER));
            if (database != null) { database.close(); database = null; }

            Map<Integer, PreviewData> previews = new HashMap<>();
            PreviewData selectedPreview = buildPreviewData(states[detailedDimension], detailedDimension, player);
            previews.put(detailedDimension, selectedPreview);
            int cacheBudget = Math.max(0, 30000 - selectedPreview.getChunkCount());
            boolean[] considered = new boolean[3];
            considered[detailedDimension] = true;
            for (int i = 0; i < 2; i++) {
                int next = -1;
                for (int candidate = 0; candidate < 3; candidate++) {
                    if (considered[candidate]) continue;
                    if (next < 0 || states[candidate].columns.size() < states[next].columns.size()) next = candidate;
                }
                if (next < 0) break;
                considered[next] = true;
                if (states[next].columns.size() > cacheBudget) continue;
                if (Thread.currentThread().isInterrupted()) throw new IOException("Preview scan cancelled.");
                previews.put(next, buildPreviewData(states[next], next, player));
                cacheBudget -= states[next].columns.size();
            }
            return previews;
        } catch (RuntimeException exception) {
            throw new IOException("Could not read the world's Bedrock database: " + safeMessage(exception), exception);
        } finally {
            if (database != null) try { database.close(); } catch (Exception ignored) { }
        }
    }

    private static int dimensionForRecord(byte[] key) {
        if (key == null) return -1;
        if (key.length == 9 && isColumnTerrainKey(key, 0)) return 0;
        if (key.length == 10 && isSubChunkKey(key, 0)) return 0;
        if (key.length == 13 || key.length == 14) {
            int dimensionId = readIntLE(key, 8);
            if (dimensionId < 1 || dimensionId > 2) return -1;
            if (key.length == 13 && isColumnTerrainKey(key, dimensionId)) return dimensionId;
            if (key.length == 14 && isSubChunkKey(key, dimensionId)) return dimensionId;
        }
        return -1;
    }

    private static PreviewData buildPreviewData(DimensionScanState state, int dimensionId, PlayerPosition player) {
        Map<Long, int[]> tiles = new HashMap<>(Math.max(16, state.columns.size() * 4 / 3));
        boolean hasBlockData = false;
        boolean hasBiomeOrHeightData = false;
        for (long chunkKey : state.columns) {
            if (Thread.currentThread().isInterrupted()) break;
            TileBuilder builder = state.builders.get(chunkKey);
            byte[] data2d = state.data2dRecords.get(chunkKey);
            byte[] data2dLegacy = state.data2dLegacyRecords.get(chunkKey);
            byte[] data3d = state.data3dRecords.get(chunkKey);
            byte[] heightSource = data2d != null ? data2d : data2dLegacy;
            int[] coarsePixels = expandCoarseTile(makeTile(heightSource, data3d, dimensionId));
            if ((data2d != null && data2d.length >= 512)
                    || (data2dLegacy != null && data2dLegacy.length >= 512)
                    || (data3d != null && data3d.length >= 512)) {
                hasBiomeOrHeightData = true;
            }
            int[] pixels;
            if (builder != null && builder.surfaceCount > 0) {
                pixels = builder.colors.clone();
                for (int i = 0; i < 256; i++) if (!builder.seen[i]) pixels[i] = coarsePixels[i];
                hasBlockData = true;
            } else {
                pixels = coarsePixels;
            }
            tiles.put(chunkKey, pixels);
        }
        if (state.columns.isEmpty()) {
            return new PreviewData(tiles, 0, -1, 0, -1, dimensionId, false, false, player);
        }
        return new PreviewData(tiles, state.minX, state.maxX, state.minZ, state.maxZ,
                dimensionId, hasBiomeOrHeightData, hasBlockData, player);
    }

    private static final class DimensionScanState {
        final List<Long> columns = new ArrayList<>();
        final Set<Long> discoveredColumns = new HashSet<>();
        final Map<Long, TileBuilder> builders = new HashMap<>();
        final Map<Long, byte[]> data2dRecords = new HashMap<>();
        final Map<Long, byte[]> data2dLegacyRecords = new HashMap<>();
        final Map<Long, byte[]> data3dRecords = new HashMap<>();
        int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
        int maxX = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
    }

'''
s = s[:start] + new + s[end:]
engine.write_text(s)

activity = Path('app/src/main/java/com/worldbridge/app/MainActivity.java')
a = activity.read_text()
a = a.replace('import java.util.Map;\n', 'import java.util.Map;\nimport java.util.Set;\n')
a = a.replace('''    private final Map<Integer, BedrockWorldPreview.PreviewData> previewCache = new ConcurrentHashMap<>();
    private Future<?> previewTask;
    private Future<?> prefetchTask;''', '''    private final Map<Integer, BedrockWorldPreview.PreviewData> previewCache = new ConcurrentHashMap<>();
    private final Set<Integer> detailReadyDimensions = ConcurrentHashMap.newKeySet();
    private Future<?> previewTask;''')
a = a.replace('''        previewCache.clear();
        setBusy(true, "Importing the world and preparing a protected copy…");''', '''        previewCache.clear();
        detailReadyDimensions.clear();
        setBusy(true, "Importing the world and preparing a protected copy…");''')
a = a.replace('''                    previewCache.clear();
                    lastExportUri = null;''', '''                    previewCache.clear();
                    detailReadyDimensions.clear();
                    lastExportUri = null;''', 1)
a = a.replace('''        Future<?> task = previewTask;
        Future<?> warmup = prefetchTask;
        previewTask = null;
        prefetchTask = null;
        if (task != null) task.cancel(true);
        if (warmup != null) warmup.cancel(true);''', '''        Future<?> task = previewTask;
        previewTask = null;
        if (task != null) task.cancel(true);''')

start = a.index('    private void loadWorldPreview() {')
end = a.index('    private void updatePreviewStatus(', start)
loader = r'''    private void loadWorldPreview() {
        if (!worldLoaded || mapView == null) return;
        final int requestId = ++previewRequestId;
        final int dimensionId = dimensionSpinner.getSelectedItemPosition();
        Future<?> previous = previewTask;
        if (previous != null) previous.cancel(true);

        BedrockWorldPreview.PreviewData cached = previewCache.get(dimensionId);
        boolean detailedAlreadyCached = detailReadyDimensions.contains(dimensionId) || cached.getChunkCount() == 0;
        if (cached != null) {
            previewStatus.setText(detailedAlreadyCached
                    ? "Showing cached preview…"
                    : "Showing quick map · loading block detail in background…");
            previewTask = previewWorker.submit(() -> {
                try {
                    android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DEFAULT);
                    Bitmap quickOverview = WorldPreviewView.createOverviewBitmap(cached);
                    runOnUiThread(() -> {
                        if (requestId != previewRequestId || !worldLoaded) {
                            if (quickOverview != null && !quickOverview.isRecycled()) quickOverview.recycle();
                            return;
                        }
                        mapView.setPreview(cached, quickOverview);
                        mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                        if (detailedAlreadyCached) updatePreviewStatus(cached);
                        else previewStatus.setText(String.format(
                                "Showing quick map · %,d chunk columns · loading block detail…", cached.getChunkCount()));
                    });
                    if (detailedAlreadyCached || Thread.currentThread().isInterrupted()) return;
                    BedrockWorldPreview.PreviewData detailed = scanAndCacheDimension(dimensionId, requestId);
                    if (detailed == null || Thread.currentThread().isInterrupted()) return;
                    Bitmap detailedOverview = WorldPreviewView.createOverviewBitmap(detailed);
                    runOnUiThread(() -> {
                        if (requestId != previewRequestId || !worldLoaded) {
                            if (detailedOverview != null && !detailedOverview.isRecycled()) detailedOverview.recycle();
                            return;
                        }
                        mapView.setPreview(detailed, detailedOverview);
                        mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                        updatePreviewStatus(detailed);
                    });
                } catch (Exception exception) {
                    if (Thread.currentThread().isInterrupted()) return;
                    runOnUiThread(() -> {
                        if (requestId == previewRequestId) previewStatus.setText(
                                "Map detail unavailable: " + friendlyMessage(exception));
                    });
                }
            });
            return;
        }

        previewStatus.setText("Reading the world database once and preparing all dimensions…");
        previewTask = previewWorker.submit(() -> {
            try {
                try { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DEFAULT); } catch (Exception ignored) { }
                BedrockWorldPreview.PreviewData data = scanAndCacheDimension(dimensionId, requestId);
                if (data == null || Thread.currentThread().isInterrupted()) return;
                Bitmap overview = WorldPreviewView.createOverviewBitmap(data);
                runOnUiThread(() -> {
                    if (requestId != previewRequestId || !worldLoaded) {
                        if (overview != null && !overview.isRecycled()) overview.recycle();
                        return;
                    }
                    mapView.setPreview(data, overview);
                    mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
                    updatePreviewStatus(data);
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

    private BedrockWorldPreview.PreviewData scanAndCacheDimension(int dimensionId, int requestId) throws Exception {
        Map<Integer, BedrockWorldPreview.PreviewData> allPreviews;
        synchronized (worldDbLock) {
            allPreviews = BedrockWorldPreview.scanAll(workingWorld, dimensionId, (partial, columnsSeen) -> {
                if (partial != null || Thread.currentThread().isInterrupted()) return;
                runOnUiThread(() -> {
                    if (requestId == previewRequestId && worldLoaded) {
                        previewStatus.setText(String.format(
                                "Reading world database · %,d chunk columns found…", columnsSeen));
                    }
                });
            });
            if (Thread.currentThread().isInterrupted()) return null;
            cachePreviewSet(allPreviews, dimensionId);
        }
        return allPreviews.get(dimensionId);
    }

    private void cachePreviewSet(Map<Integer, BedrockWorldPreview.PreviewData> allPreviews, int detailedDimension) {
        BedrockWorldPreview.PreviewData detailed = allPreviews.get(detailedDimension);
        if (detailed != null) {
            previewCache.put(detailedDimension, detailed);
            detailReadyDimensions.add(detailedDimension);
        }
        for (int dimension = 0; dimension < 3; dimension++) {
            if (dimension == detailedDimension || detailReadyDimensions.contains(dimension)) continue;
            BedrockWorldPreview.PreviewData quick = allPreviews.get(dimension);
            if (quick != null) {
                previewCache.putIfAbsent(dimension, quick);
                if (quick.getChunkCount() == 0) detailReadyDimensions.add(dimension);
            }
        }

        int totalChunks = 0;
        for (BedrockWorldPreview.PreviewData cached : previewCache.values()) totalChunks += cached.getChunkCount();
        if (totalChunks > 30000) {
            for (int dimension = 0; dimension < 3 && totalChunks > 30000; dimension++) {
                if (dimension == detailedDimension || detailReadyDimensions.contains(dimension)) continue;
                BedrockWorldPreview.PreviewData removed = previewCache.remove(dimension);
                if (removed != null) totalChunks -= removed.getChunkCount();
            }
            for (int dimension = 0; dimension < 3 && totalChunks > 30000; dimension++) {
                if (dimension == detailedDimension) continue;
                BedrockWorldPreview.PreviewData removed = previewCache.remove(dimension);
                if (removed != null) totalChunks -= removed.getChunkCount();
                detailReadyDimensions.remove(dimension);
            }
        }
    }

'''
a = a[:start] + loader + a[end:]
if '    private void prefetchOtherDimensions(' in a:
    start = a.index('    private void prefetchOtherDimensions(')
    end = a.index('    private void updatePreviewStatus(', start)
    a = a[:start] + a[end:]
a = a.replace('''        previewCache.clear();
        setBusy(true, "Restoring the original working copy…");''', '''        previewCache.clear();
        detailReadyDimensions.clear();
        setBusy(true, "Restoring the original working copy…");''')
a = a.replace('''                    previewCache.clear();
                }''', '''                    previewCache.clear();
                    detailReadyDimensions.clear();
                }''', 1)
activity.write_text(a)
print('Installed one-pass multi-dimension scanner and quick-map/detail-on-first-visit flow.')
