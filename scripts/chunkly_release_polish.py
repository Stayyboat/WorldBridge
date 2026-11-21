from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path('.')
MAIN = ROOT / 'app/src/main/java/com/worldbridge/app/MainActivity.java'
PREVIEW = ROOT / 'app/src/main/java/com/worldbridge/app/WorldPreviewView.java'
FILES = ROOT / 'app/src/main/java/com/worldbridge/app/WorldFiles.java'
PRUNER = ROOT / 'engine/src/main/java/com/worldbridge/engine/BedrockChunkPruner.java'
SETTINGS = ROOT / 'settings.gradle.kts'
MANIFEST = ROOT / 'app/src/main/AndroidManifest.xml'
ANDROID = '{http://schemas.android.com/apk/res/android}'


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    return source.replace(old, new, 1)


# Stable product name and Android 11+ edge-to-edge / keyboard handling.
main = MAIN.read_text()
main = main.replace('import android.graphics.Bitmap;\n', 'import android.graphics.Bitmap;\nimport android.graphics.Insets;\n')
main = main.replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport android.os.Build;\n')
main = main.replace('import android.text.InputType;\n', 'import android.text.InputType;\nimport android.text.TextUtils;\n')
main = main.replace('import android.view.ViewGroup;\n', 'import android.view.ViewGroup;\nimport android.view.WindowInsets;\nimport android.view.WindowManager;\n')
for line in ('import android.widget.ArrayAdapter;\n', 'import android.widget.AdapterView;\n', 'import android.widget.Spinner;\n'):
    main = main.replace(line, '')
main = main.replace('    private Spinner dimensionSpinner;\n', '')
main = replace_once(main,
'''        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(0);
''',
'''        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            getWindow().setNavigationBarContrastEnforced(false);
        }
''', 'window setup')
main = main.replace('TextView title = label("WorldBridge", 30, TEXT, true);',
                    'TextView title = label("Chunkly", 30, TEXT, true);')

old_world = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        importCard.addView(importButton, matchWrap());
        importButton.setTranslationY(dp(12));
        worldStatus = label(worldName, 13, MUTED, false);
        worldStatus.setPadding(0, dp(10), 0, 0);
        importCard.addView(worldStatus);

        LinearLayout worldActions = new LinearLayout(this);
        worldActions.setOrientation(LinearLayout.HORIZONTAL);
        worldActions.setGravity(Gravity.END);
        deleteWorldButton = actionButton("Delete world", PANEL_SOFT, TEXT);
        deleteWorldButton.setTextSize(12);
        deleteWorldButton.setPadding(dp(12), 0, dp(12), 0);
        deleteWorldButton.setMinHeight(0);
        deleteWorldButton.setMinimumHeight(dp(34));
        deleteWorldButton.setBackground(roundRect(PANEL_SOFT, dp(10), BORDER, dp(1)));
        deleteWorldButton.setOnClickListener(v -> confirmDeleteWorld());
        LinearLayout.LayoutParams deleteWorldParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(34));
        deleteWorldParams.topMargin = dp(8);
        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, matchWrap());
'''
new_world = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        LinearLayout.LayoutParams importParams = matchWrap();
        importParams.topMargin = dp(12);
        importCard.addView(importButton, importParams);

        LinearLayout worldActions = new LinearLayout(this);
        worldActions.setOrientation(LinearLayout.HORIZONTAL);
        worldActions.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams worldActionsParams = matchWrap();
        worldActionsParams.topMargin = dp(10);

        worldStatus = label(worldName, 13, MUTED, false);
        worldStatus.setGravity(Gravity.CENTER_VERTICAL);
        worldStatus.setSingleLine(true);
        worldStatus.setEllipsize(TextUtils.TruncateAt.END);
        worldStatus.setMinHeight(dp(34));
        LinearLayout.LayoutParams worldStatusParams = new LinearLayout.LayoutParams(
                0, dp(34), 1f);
        worldActions.addView(worldStatus, worldStatusParams);

        deleteWorldButton = actionButton("Delete world", PANEL_SOFT, TEXT);
        deleteWorldButton.setTextSize(12);
        deleteWorldButton.setPadding(dp(12), 0, dp(12), 0);
        deleteWorldButton.setMinHeight(0);
        deleteWorldButton.setMinimumHeight(dp(34));
        deleteWorldButton.setBackground(roundRect(PANEL_SOFT, dp(10), BORDER, dp(1)));
        deleteWorldButton.setOnClickListener(v -> confirmDeleteWorld());
        LinearLayout.LayoutParams deleteWorldParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(34));
        deleteWorldParams.leftMargin = dp(10);
        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, worldActionsParams);
'''
main = replace_once(main, old_world, new_world, 'World card layout')

spinner = '''        dimensionSpinner = new Spinner(this);
        String[] dimensions = {"Overworld", "Nether", "The End"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, dimensions);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        dimensionSpinner.setAdapter(adapter);
        dimensionSpinner.setOnItemSelectedListener(null);

        // Keep the Spinner as the single source of selected-dimension state so all
        // existing preview, cache, and pruning logic remains unchanged.
        dimensionSpinner.setVisibility(View.GONE);
'''
main = replace_once(main, spinner, '', 'unused hidden dimension spinner')
main = main.replace('        if (dimensionSpinner != null) dimensionSpinner.setSelection(index);\n', '')
main = main.replace('                    if (dimensionSpinner != null) dimensionSpinner.setSelection(0);\n', '')

main = replace_once(main,
'''        scroll.setClipToPadding(false);
        scroll.setBackgroundColor(BG);
''',
'''        scroll.setClipToPadding(true);
        scroll.setBackgroundColor(BG);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            scroll.setOnApplyWindowInsetsListener((view, insets) -> {
                Insets safeInsets = insets.getInsets(
                        WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout()
                                | WindowInsets.Type.ime());
                view.setPadding(safeInsets.left, safeInsets.top,
                        safeInsets.right, safeInsets.bottom);
                return insets;
            });
        }
''', 'edge-to-edge inset handling')
main = main.replace('''        setContentView(scroll);
        animateCards(content);''',
'''        setContentView(scroll);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) scroll.requestApplyInsets();
        setTitle("Chunkly");
        animateCards(content);''')
heading_metrics = '''        view.setIncludeFontPadding(false);
        view.setLetterSpacing(0.01f);
        view.setPadding(0, dp(6), 0, dp(6));'''
if main.count(heading_metrics) != 1:
    raise SystemExit('Shared section heading metrics are not using balanced 6dp top/bottom padding.')

main = replace_once(main,
'''        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;''',
'''        view.setTextColor(color);
        view.setIncludeFontPadding(false);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;''', 'label text metrics')
main = replace_once(main,
'''        button.setTextSize(14);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setTextColor(foreground);
        button.setPadding(dp(14), dp(5), dp(14), dp(5));
        button.setBackground(roundRect(background, dp(14), background, 0));''',
'''        button.setTextSize(14);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setTextColor(foreground);
        button.setGravity(Gravity.CENTER);
        button.setIncludeFontPadding(false);
        button.setSingleLine(true);
        button.setMinHeight(dp(48));
        button.setMinimumHeight(dp(48));
        button.setPadding(dp(14), dp(5), dp(14), dp(5));
        button.setBackground(roundRect(background, dp(14), background, 0));''', 'button metrics')
MAIN.write_text(main)

# Purple selection overlay and null-safe gesture parent handling.
preview = PREVIEW.read_text()
preview = preview.replace('private final int selectionFill = 0x667CE0A4;', 'private final int selectionFill = 0x55B69CFF;')
preview = preview.replace('private final int selectionStroke = 0xFF7CE0A4;', 'private final int selectionStroke = 0xFFB69CFF;')
preview = preview.replace('if (getParent() != null) getParent().requestDisallowInterceptTouchEvent(true);', 'requestParentIntercept(true);')
preview = preview.replace('if (getParent() != null) getParent().requestDisallowInterceptTouchEvent(false);', 'requestParentIntercept(false);')
preview = preview.replace('getParent().requestDisallowInterceptTouchEvent(true);', 'requestParentIntercept(true);')
preview = preview.replace('getParent().requestDisallowInterceptTouchEvent(false);', 'requestParentIntercept(false);')
if 'private void requestParentIntercept(boolean disallow)' not in preview:
    preview = replace_once(preview, '    @Override\n    public boolean onTouchEvent(MotionEvent event) {',
'''    private void requestParentIntercept(boolean disallow) {
        android.view.ViewParent parent = getParent();
        if (parent != null) parent.requestDisallowInterceptTouchEvent(disallow);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {''', 'safe parent gesture helper')
PREVIEW.write_text(preview)

# Allow significantly closer inspection while preserving the original fit scale.
preview = PREVIEW.read_text()
preview = replace_once(
    preview,
    "float next = Math.max(baseScale * 0.55f, Math.min(baseScale * 24f, scale * detector.getScaleFactor()));",
    "float maxZoom = preview != null && preview.dimensionId == 0 ? 128f : 64f;\n                float next = Math.max(baseScale * 0.55f, Math.min(baseScale * maxZoom, scale * detector.getScaleFactor()));",
    "maximum preview zoom"
)
PREVIEW.write_text(preview)

# Bound both the compressed .mcworld copy and decompressed contents; remove partial copies.
files = FILES.read_text()
files = replace_once(files,
'''        try (InputStream input = resolver.openInputStream(uri);
             OutputStream output = new BufferedOutputStream(new FileOutputStream(destination))) {
            if (input == null) throw new IOException("Android could not open that file.");
            byte[] buffer = new byte[BUFFER_SIZE];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
        }
''',
'''        boolean complete = false;
        try (InputStream input = resolver.openInputStream(uri)) {
            if (input == null) throw new IOException("Android could not open that file.");
            try (OutputStream output = new BufferedOutputStream(new FileOutputStream(destination))) {
                byte[] buffer = new byte[BUFFER_SIZE];
                long copied = 0;
                int read;
                while ((read = input.read(buffer)) != -1) {
                    copied += read;
                    if (copied > MAX_UNPACKED_BYTES) {
                        throw new IOException("The selected world archive is larger than the 6 GB safety limit.");
                    }
                    output.write(buffer, 0, read);
                }
            }
            complete = true;
        } finally {
            if (!complete && destination.exists() && !destination.delete()) {
                // The import staging folder is also cleaned by the caller on failure.
            }
        }
''', 'bounded archive copy')
FILES.write_text(files)

main = MAIN.read_text()
main = replace_once(main,
'''                } catch (Exception ignored) {
                    // Keep any remaining backup directories rather than deleting the only recoverable copy.
                }
                runOnUiThread(() -> {
''',
'''                } catch (Exception ignored) {
                    // Keep any remaining backup directories rather than deleting the only recoverable copy.
                }
                try {
                    WorldFiles.deleteRecursively(staging);
                } catch (Exception ignored) {
                    // A leftover staging directory is harmless and can be removed on the next import.
                }
                runOnUiThread(() -> {
''', 'failed import staging cleanup')
main = main.replace('from WorldBridge.', 'from Chunkly.')
main = main.replace('World deleted from WorldBridge.', 'World deleted from Chunkly.')
MAIN.write_text(main)

# More accurate chunk/actor counts; skip full-database compaction for an empty selection.
pruner = PRUNER.read_text()
pruner = pruner.replace('''        long recordCount = 0;
        long columnCount = 0;
        long tileEntityRecordCount = 0;''',
'''        long recordCount = 0;
        Set<Long> selectedChunkColumns = new HashSet<>();
        long tileEntityRecordCount = 0;''')
pruner = replace_once(pruner,
'''                        recordCount++;
                        if (parsed.isColumnVersion) columnCount++;
                        if (parsed.recordType == BLOCK_ENTITY) tileEntityRecordCount++;''',
'''                        recordCount++;
                        selectedChunkColumns.add((((long) parsed.chunkX) << 32)
                                | (parsed.chunkZ & 0xFFFFFFFFL));
                        if (parsed.recordType == BLOCK_ENTITY) tileEntityRecordCount++;''',
'unique selected chunk column accounting')
pruner = replace_once(pruner,
'''                        ByteBuffer.wrap(actorKey, ACTOR_PREFIX.length, 8)
                                .order(ByteOrder.LITTLE_ENDIAN).putLong(id);
                        writeSpoolKey(spool, actorKey);
                        recordCount++;
                        actorPayloadRecordCount++;''',
'''                        ByteBuffer.wrap(actorKey, ACTOR_PREFIX.length, 8)
                                .order(ByteOrder.LITTLE_ENDIAN).putLong(id);
                        if (database.get(actorKey) != null) {
                            writeSpoolKey(spool, actorKey);
                            recordCount++;
                            actorPayloadRecordCount++;
                        }''', 'existing actor payload validation')
pruner = replace_once(pruner,
'''            // Compact tombstones so the exported world can reclaim deleted chunk storage.
            // This is the same final LevelDB compaction step used by Chunker.
            database.compactRange(null, null);''',
'''            // Empty selections should not trigger an expensive full-database compaction.
            if (recordCount > 0) database.compactRange(null, null);''', 'skip empty compaction')
pruner = replace_once(pruner, 'return new Result(columnCount, recordCount,',
                     'return new Result(selectedChunkColumns.size(), recordCount,',
                     'correct unique chunk count result')
PRUNER.write_text(pruner)

# Product label only: preserve application ID, Java packages, app data folder and prefs.
if MANIFEST.exists():
    tree = ET.parse(MANIFEST)
    root = tree.getroot()
    app = root.find('application')
    if app is None:
        raise SystemExit('AndroidManifest.xml has no application element')
    app.set(ANDROID + 'label', 'Chunkly')
    for node in root.iter():
        if node.tag not in ('activity', 'activity-alias'):
            continue
        is_launcher = any(
            any(child.tag == 'action' and child.get(ANDROID + 'name') == 'android.intent.action.MAIN'
                for child in list(intent_filter))
            and any(child.tag == 'category' and child.get(ANDROID + 'name') == 'android.intent.category.LAUNCHER'
                    for child in list(intent_filter))
            for intent_filter in node.findall('intent-filter')
        )
        if is_launcher:
            node.set(ANDROID + 'label', 'Chunkly')
    ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
    tree.write(MANIFEST, encoding='utf-8', xml_declaration=True)
else:
    raise SystemExit('AndroidManifest.xml is missing; refusing to build without the Chunkly app label.')

if SETTINGS.exists():
    settings = SETTINGS.read_text()
    settings = replace_once(settings, 'rootProject.name = "WorldBridge"',
                             'rootProject.name = "Chunkly"', 'Gradle project display name')
    SETTINGS.write_text(settings)

print('Chunkly release polish applied successfully.')
