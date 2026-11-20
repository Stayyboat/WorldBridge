from pathlib import Path

# Extend BedrockChunkPruner to remove both legacy chunk entity data and modern
# 1.18.30+ actor digest/payload records, while retaining them when the toggle is off.
p = Path("engine/src/main/java/com/worldbridge/engine/BedrockChunkPruner.java")
s = p.read_text()
def replace_once(source, old, new, label):
    if old not in source:
        raise SystemExit("Expected source block not found: " + label)
    return source.replace(old, new, 1)

s = replace_once(s,
    "import java.util.Arrays;\nimport java.util.Map;\n",
    "import java.util.Arrays;\nimport java.util.HashSet;\nimport java.util.Map;\nimport java.util.Set;\n", "pruner imports")
s = replace_once(s,
    "    private static final byte LEGACY_VERSION = 118;\n",
    "    private static final byte LEGACY_VERSION = 118;\n"
    "    private static final byte BLOCK_ENTITY = 49;\n"
    "    private static final byte LEGACY_ENTITY = 50;\n"
    "    private static final byte[] ACTOR_DIGEST_PREFIX = \"digp\".getBytes(StandardCharsets.US_ASCII);\n"
    "    private static final byte[] ACTOR_PREFIX = \"actorprefix\".getBytes(StandardCharsets.US_ASCII);\n",
    "Bedrock record constants")

old = """    public static Result prune(
            File worldDirectory,
            int dimensionId,
            int minChunkX,
            int minChunkZ,
            int maxChunkX,
            int maxChunkZ,
            File scratchDirectory
    ) throws IOException {
        validate(worldDirectory, dimensionId, minChunkX, minChunkZ, maxChunkX, maxChunkZ);"""
new = """    public static Result prune(
            File worldDirectory, int dimensionId, int minChunkX, int minChunkZ,
            int maxChunkX, int maxChunkZ, File scratchDirectory
    ) throws IOException {
        return prune(worldDirectory, dimensionId, minChunkX, minChunkZ,
                maxChunkX, maxChunkZ, scratchDirectory, true);
    }

    public static Result prune(
            File worldDirectory,
            int dimensionId,
            int minChunkX,
            int minChunkZ,
            int maxChunkX,
            int maxChunkZ,
            File scratchDirectory,
            boolean removeSavedData
    ) throws IOException {
        validate(worldDirectory, dimensionId, minChunkX, minChunkZ, maxChunkX, maxChunkZ);"""
s = replace_once(s, old, new, "pruner overload")
s = replace_once(s,
    "        long recordCount = 0;\n        long columnCount = 0;\n        DB database = null;",
    "        long recordCount = 0;\n        long columnCount = 0;\n"
    "        long tileEntityRecordCount = 0;\n"
    "        long legacyEntityRecordCount = 0;\n"
    "        long actorDigestRecordCount = 0;\n"
    "        long actorPayloadRecordCount = 0;\n"
    "        Set<Long> selectedActorIds = new HashSet<>();\n"
    "        DB database = null;", "pruner counters")

old = """                    ParsedChunkKey parsed = parseChunkKey(key);
                    if (parsed == null) continue;
                    if (parsed.dimensionId != dimensionId) continue;
                    if (parsed.chunkX < minChunkX || parsed.chunkX > maxChunkX
                            || parsed.chunkZ < minChunkZ || parsed.chunkZ > maxChunkZ) {
                        continue;
                    }

                    spool.writeInt(key.length);
                    spool.write(key);
                    recordCount++;
                    if (parsed.isColumnVersion) columnCount++;"""
new = """                    ParsedChunkKey parsed = parseChunkKey(key);
                    if (parsed != null && inSelection(parsed.chunkX, parsed.chunkZ, parsed.dimensionId,
                            dimensionId, minChunkX, minChunkZ, maxChunkX, maxChunkZ)) {
                        if (!removeSavedData && (parsed.recordType == BLOCK_ENTITY
                                || parsed.recordType == LEGACY_ENTITY)) continue;
                        writeSpoolKey(spool, key);
                        recordCount++;
                        if (parsed.isColumnVersion) columnCount++;
                        if (parsed.recordType == BLOCK_ENTITY) tileEntityRecordCount++;
                        if (parsed.recordType == LEGACY_ENTITY) legacyEntityRecordCount++;
                        continue;
                    }

                    // Modern Bedrock stores entity IDs in digp<chunk-key> values.
                    ParsedDigest digest = removeSavedData ? parseDigestKey(key) : null;
                    if (digest != null && inSelection(digest.x, digest.z, digest.dimension,
                            dimensionId, minChunkX, minChunkZ, maxChunkX, maxChunkZ)) {
                        byte[] ids = entry.getValue();
                        if ((ids.length % 8) != 0) {
                            throw new IOException("A selected chunk has an invalid actor digest. No records were deleted.");
                        }
                        writeSpoolKey(spool, key);
                        recordCount++;
                        actorDigestRecordCount++;
                        for (int offset = 0; offset < ids.length; offset += 8) {
                            selectedActorIds.add(ByteBuffer.wrap(ids, offset, 8)
                                    .order(ByteOrder.LITTLE_ENDIAN).getLong());
                        }
                    }"""
s = replace_once(s, old, new, "pruner first pass")

anchor = "            // Second pass: delete in bounded batches to keep memory predictable.\n"
insert = """            // Protect actor IDs that are also referenced by a digest outside the selection.
            if (removeSavedData && !selectedActorIds.isEmpty()) {
                try (DBIterator iterator = database.iterator(new ReadOptions().fillCache(false))) {
                    while (iterator.hasNext() && !selectedActorIds.isEmpty()) {
                        Map.Entry<byte[], byte[]> entry = iterator.next();
                        ParsedDigest digest = parseDigestKey(entry.getKey());
                        if (digest == null || inSelection(digest.x, digest.z, digest.dimension,
                                dimensionId, minChunkX, minChunkZ, maxChunkX, maxChunkZ)) continue;
                        byte[] ids = entry.getValue();
                        if ((ids.length % 8) != 0) {
                            throw new IOException("An unselected chunk has an invalid actor digest. No records were deleted.");
                        }
                        for (int offset = 0; offset < ids.length; offset += 8) {
                            selectedActorIds.remove(ByteBuffer.wrap(ids, offset, 8)
                                    .order(ByteOrder.LITTLE_ENDIAN).getLong());
                        }
                    }
                }
                // actorprefix + the exact 8 storage-ID bytes from the digest.
                try (DataOutputStream spool = new DataOutputStream(
                        new BufferedOutputStream(new FileOutputStream(keySpool, true)))) {
                    for (Long id : selectedActorIds) {
                        byte[] actorKey = new byte[ACTOR_PREFIX.length + 8];
                        System.arraycopy(ACTOR_PREFIX, 0, actorKey, 0, ACTOR_PREFIX.length);
                        ByteBuffer.wrap(actorKey, ACTOR_PREFIX.length, 8)
                                .order(ByteOrder.LITTLE_ENDIAN).putLong(id);
                        writeSpoolKey(spool, actorKey);
                        recordCount++;
                        actorPayloadRecordCount++;
                    }
                }
            }

""" + anchor
s = replace_once(s, anchor, insert, "actor cleanup pass")
s = replace_once(s,
    "                            if (length < 9 || length > 14) {\n                                throw new IOException(\"Invalid temporary chunk key length.\");\n                            }",
    "                            if (length < 9 || length > ACTOR_PREFIX.length + 8) {\n                                throw new IOException(\"Invalid temporary LevelDB key length.\");\n                            }",
    "spool key length")
s = replace_once(s,
    "            return new Result(columnCount, recordCount);",
    "            return new Result(columnCount, recordCount,\n"
    "                    legacyEntityRecordCount + actorDigestRecordCount + actorPayloadRecordCount,\n"
    "                    tileEntityRecordCount);", "pruner result")

helpers = """    private static void writeSpoolKey(DataOutputStream spool, byte[] key) throws IOException {
        spool.writeInt(key.length);
        spool.write(key);
    }

    private static boolean inSelection(int x, int z, int recordDimension, int selectedDimension,
                                       int minX, int minZ, int maxX, int maxZ) {
        return recordDimension == selectedDimension && x >= minX && x <= maxX
                && z >= minZ && z <= maxZ;
    }

    // digp + x + z [+ dimension], with little-endian 32-bit coordinates.
    private static ParsedDigest parseDigestKey(byte[] key) {
        if (key == null || (key.length != 12 && key.length != 16)) return null;
        for (int i = 0; i < ACTOR_DIGEST_PREFIX.length; i++) {
            if (key[i] != ACTOR_DIGEST_PREFIX[i]) return null;
        }
        ByteBuffer b = ByteBuffer.wrap(key, 4, key.length - 4).order(ByteOrder.LITTLE_ENDIAN);
        int x = b.getInt();
        int z = b.getInt();
        int dimension = b.hasRemaining() ? b.getInt() : 0;
        if (dimension < 0 || dimension > 2) return null;
        return new ParsedDigest(x, z, dimension);
    }

    private static final class ParsedDigest {
        final int x, z, dimension;
        ParsedDigest(int x, int z, int dimension) {
            this.x = x; this.z = z; this.dimension = dimension;
        }
    }

"""
s = replace_once(s,
    "    /**\n     * Parse the Bedrock chunk key forms used by Chunker:",
    helpers + "    /**\n     * Parse the Bedrock chunk key forms used by Chunker:",
    "digest helper insertion")
s = replace_once(s,
    "        return new ParsedChunkKey(x, z, dimension, versionKey);",
    "        return new ParsedChunkKey(x, z, dimension, versionKey, type);",
    "chunk record type")
s = replace_once(s,
    """        final boolean isColumnVersion;

        ParsedChunkKey(int chunkX, int chunkZ, int dimensionId, boolean isColumnVersion) {
            this.chunkX = chunkX;
            this.chunkZ = chunkZ;
            this.dimensionId = dimensionId;
            this.isColumnVersion = isColumnVersion;
        }""",
    """        final boolean isColumnVersion;
        final byte recordType;

        ParsedChunkKey(int chunkX, int chunkZ, int dimensionId, boolean isColumnVersion, byte recordType) {
            this.chunkX = chunkX;
            this.chunkZ = chunkZ;
            this.dimensionId = dimensionId;
            this.isColumnVersion = isColumnVersion;
            this.recordType = recordType;
        }""", "chunk key class")
s = replace_once(s,
    """    public static final class Result {
        public final long chunkColumns;
        public final long recordsDeleted;

        public Result(long chunkColumns, long recordsDeleted) {
            this.chunkColumns = chunkColumns;
            this.recordsDeleted = recordsDeleted;
        }
    }""",
    """    public static final class Result {
        public final long chunkColumns;
        public final long recordsDeleted;
        public final long savedEntityRecordsDeleted;
        public final long tileEntityRecordsDeleted;

        public Result(long chunkColumns, long recordsDeleted,
                      long savedEntityRecordsDeleted, long tileEntityRecordsDeleted) {
            this.chunkColumns = chunkColumns;
            this.recordsDeleted = recordsDeleted;
            this.savedEntityRecordsDeleted = savedEntityRecordsDeleted;
            this.tileEntityRecordsDeleted = tileEntityRecordsDeleted;
        }
    }""", "result class")
p.write_text(s)

# Add the default-on toggle to the Review and prune section.
p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
m = p.read_text()
m = replace_once(m, "import android.content.SharedPreferences;\n",
    "import android.content.SharedPreferences;\nimport android.content.res.ColorStateList;\n", "ColorStateList import")
m = replace_once(m, "import android.widget.Button;\n",
    "import android.widget.Button;\nimport android.widget.CheckBox;\n", "CheckBox import")
m = replace_once(m, "    private Button pruneButton;\n",
    "    private Button pruneButton;\n    private CheckBox cleanupSavedDataToggle;\n", "toggle field")

old = """        actionHint.setPadding(0, dp(7), 0, dp(12));
        actionCard.addView(actionHint);

        pruneButton = actionButton("Review selected area", ACCENT, BG);"""
new = """        actionHint.setPadding(0, dp(7), 0, dp(8));
        actionCard.addView(actionHint);

        cleanupSavedDataToggle = new CheckBox(this);
        cleanupSavedDataToggle.setText("Also remove saved mobs, entities, dropped items & tile entities");
        cleanupSavedDataToggle.setTextColor(TEXT);
        cleanupSavedDataToggle.setTextSize(14);
        cleanupSavedDataToggle.setButtonTintList(ColorStateList.valueOf(ACCENT));
        cleanupSavedDataToggle.setChecked(true);
        cleanupSavedDataToggle.setPadding(0, dp(2), 0, dp(4));
        actionCard.addView(cleanupSavedDataToggle, matchWrap());
        TextView cleanupHint = label("Targets only saved data tied to the selected chunks and dimension. Dedicated player save records are kept.", 12, MUTED, false);
        cleanupHint.setPadding(dp(36), 0, 0, dp(12));
        actionCard.addView(cleanupHint);

        pruneButton = actionButton("Review selected area", ACCENT, BG);"""
m = replace_once(m, old, new, "review toggle UI")

old = """        String details = "Dimension: " + dimensionName
                + "\\nChunk X: " + selectionMinX + " through " + selectionMaxX
                + "\\nChunk Z: " + selectionMinZ + " through " + selectionMaxZ
                + "\\nRectangle size: " + String.format("%,d", columns) + " chunk positions"
                + "\\n\\nOnly records belonging to chunk columns inside this rectangle will be deleted. All other dimensions and all chunks outside the rectangle are kept.\\n\\nThe imported .mcworld file and the protected original copy are not changed.";

        new AlertDialog.Builder(this)
                .setTitle("Review chunk removal")
                .setMessage(details)
                .setNegativeButton("Go back", null)
                .setPositiveButton("Delete selected chunks", (dialog, which) -> pruneSelected(dimensionIndex))
                .show();"""
new = """        final boolean removeSavedData = cleanupSavedDataToggle != null && cleanupSavedDataToggle.isChecked();
        String cleanupSummary = removeSavedData
                ? "\\n\\nSaved-data cleanup: ON\\nSaved mobs, entities and dropped items (legacy and modern Bedrock actor storage) plus tile entities in these chunk positions will also be removed."
                : "\\n\\nSaved-data cleanup: OFF\\nMobs, entities, dropped items and tile-entity records will be left at these pruned chunk positions. They may become orphaned data.";
        String details = "Dimension: " + dimensionName
                + "\\nChunk X: " + selectionMinX + " through " + selectionMaxX
                + "\\nChunk Z: " + selectionMinZ + " through " + selectionMaxZ
                + "\\nRectangle size: " + String.format("%,d", columns) + " chunk positions"
                + cleanupSummary
                + "\\n\\nAll other dimensions and chunks outside this rectangle are kept. Dedicated player save records are not removed. The imported .mcworld file and protected original copy are not changed.";

        new AlertDialog.Builder(this)
                .setTitle("Review chunk removal")
                .setMessage(details)
                .setNegativeButton("Go back", null)
                .setPositiveButton("Delete selected chunks", (dialog, which) -> pruneSelected(dimensionIndex, removeSavedData))
                .show();"""
m = replace_once(m, old, new, "review dialog")
m = replace_once(m, "    private void pruneSelected(int dimensionIndex) {",
    "    private void pruneSelected(int dimensionIndex, boolean removeSavedData) {", "prune method signature")
m = replace_once(m,
    """                    result = BedrockChunkPruner.prune(
                            workingWorld, dimensionId, minX, minZ, maxX, maxZ, scratch
                    );""",
    """                    result = BedrockChunkPruner.prune(
                            workingWorld, dimensionId, minX, minZ, maxX, maxZ, scratch, removeSavedData
                    );""", "pruner call")
m = replace_once(m,
    """                    actionStatus.setText("Finished: " + String.format("%,d", result.chunkColumns)
                            + " chunk columns found; " + String.format("%,d", result.recordsDeleted)
                            + " LevelDB records removed from " + dimensionName + ".");""",
    """                    actionStatus.setText("Finished: " + String.format("%,d", result.chunkColumns)
                            + " chunk columns found; " + String.format("%,d", result.recordsDeleted)
                            + " LevelDB records removed from " + dimensionName + "."
                            + (removeSavedData ? " Saved entity/actor records: "
                                    + String.format("%,d", result.savedEntityRecordsDeleted)
                                    + "; tile-entity records: "
                                    + String.format("%,d", result.tileEntityRecordsDeleted) + "." : ""));""",
    "prune completion status")
p.write_text(m)
print("Added optional cleanup for saved mobs/entities, dropped items, and tile entities.")
