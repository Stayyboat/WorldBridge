from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
PREVIEW = Path("app/src/main/java/com/worldbridge/app/WorldPreviewView.java")

main = MAIN.read_text()
preview = PREVIEW.read_text()


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


# Remove decorative eyebrow and marketing/helper subtitle; keep the product name.
main = replace_once(
    main,
    '''        TextView eyebrow = label("MINECRAFT BEDROCK TOOL", 11, ACCENT, true);
        eyebrow.setLetterSpacing(0.13f);
        content.addView(eyebrow);
        TextView title = label("WorldBridge", 32, TEXT, true);
        title.setPadding(0, dp(5), 0, 0);
        content.addView(title);
        TextView subtitle = label("Trim selected chunks. Keep everything around them.", 14, MUTED, false);
        subtitle.setPadding(0, dp(5), 0, dp(18));
        content.addView(subtitle);
''',
    '''        TextView title = label("WorldBridge", 30, TEXT, true);
        title.setPadding(0, 0, 0, dp(18));
        content.addView(title);
''',
    "header copy"
)

# Import section: retain the actionable title, button, and current-world status.
main = replace_once(main,
    'label("1  ·  Choose your world", 17, TEXT, true)',
    'label("World", 17, TEXT, true)', "world section title")
main = replace_once(main,
    '''        TextView importHint = label("Export the world from Minecraft as a .mcworld file, then open it here. Your original file is never edited.", 13, MUTED, false);
        importHint.setPadding(0, dp(7), 0, dp(12));
        importCard.addView(importHint);
''', "", "import tutorial copy")

main = replace_once(main,
    'label("2  ·  Choose a dimension", 17, TEXT, true)',
    'label("Dimension", 17, TEXT, true)', "dimension section title")
main = replace_once(main,
    'label("3  ·  Select the chunks to remove", 17, TEXT, true)',
    'label("Chunk selection", 17, TEXT, true)', "selection section title")
main = replace_once(main,
    '''        TextView selectionHint = label("Top-down world preview. Drag across the map to mark chunks; pinch to zoom and use two fingers to move around. Only the highlighted area is removed.", 13, MUTED, false);
        selectionHint.setPadding(0, dp(7), 0, dp(12));
        selectionCard.addView(selectionHint);
''', "", "selection tutorial copy")

# Preview status is only visible while there is an active preview or useful status.
main = replace_once(main,
    '''        previewStatus = label("Import a .mcworld file to build the map preview.", 12, MUTED, false);
        previewStatus.setPadding(0, dp(8), 0, 0);
        selectionCard.addView(previewStatus);
        TextView mapLegend = label("Map colours are approximate: blue = water · green = vegetation · tan = dry biomes · pale = snowy areas · red/brown = Nether biomes.", 11, MUTED, false);
        mapLegend.setPadding(0, dp(5), 0, 0);
        selectionCard.addView(mapLegend);
''',
    '''        previewStatus = label("", 12, MUTED, false);
        previewStatus.setPadding(0, dp(8), 0, 0);
        previewStatus.setVisibility(View.GONE);
        selectionCard.addView(previewStatus);
''',
    "preview helper and legend"
)

main = replace_once(main,
    '''        TextView manualHint = label("Use chunk coordinates, not block coordinates. Negative coordinates are allowed.", 12, MUTED, false);
        manualHint.setPadding(0, 0, 0, dp(8));
        manualPanel.addView(manualHint);
''', "", "coordinate tutorial copy")

main = replace_once(main,
    'label("4  ·  Review and prune", 17, TEXT, true)',
    'label("Prune", 17, TEXT, true)', "prune section title")
main = replace_once(main,
    '''        TextView actionHint = label("WorldBridge makes a separate working copy first. The .mcworld you imported stays untouched.", 13, MUTED, false);
        actionHint.setPadding(0, dp(7), 0, dp(8));
        actionCard.addView(actionHint);
''', "", "prune helper copy")
main = replace_once(main,
    'cleanupSavedDataToggle.setText("Also remove saved mobs, entities, dropped items & tile entities");',
    'cleanupSavedDataToggle.setText("Remove mobs, entities, dropped items & block entities");',
    "cleanup toggle copy")
main = replace_once(main,
    '''        TextView cleanupHint = label("Targets only saved data tied to the selected chunks and dimension. Dedicated player save records are kept.", 12, MUTED, false);
        cleanupHint.setPadding(dp(36), 0, 0, dp(12));
        actionCard.addView(cleanupHint);
''', "", "cleanup helper copy")
main = replace_once(main,
    'actionStatus = label("Ready when your world is imported.", 12, MUTED, false);',
    'actionStatus = label("Ready", 12, MUTED, false);',
    "initial action status")
main = replace_once(main,
    'label("5  ·  Export back to Minecraft", 17, TEXT, true)',
    'label("Export", 17, TEXT, true)', "export section title")
main = replace_once(main,
    '''        TextView exportHint = label("Save the edited copy as a new .mcworld file, then open that file with Minecraft.", 13, MUTED, false);
        exportHint.setPadding(0, dp(7), 0, dp(12));
        exportCard.addView(exportHint);
''', "", "export tutorial copy")
main = replace_once(main,
    '''        TextView footer = label("Offline processing  ·  No account required  ·  Minecraft Bedrock worlds only", 11, MUTED, false);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(4), 0, dp(4));
        content.addView(footer);

''', "", "decorative footer")

# Concise operational copy; keep validation errors and safety confirmations.
replacements = {
    'setBusy(true, "Importing the world and preparing a protected copy…");': 'setBusy(true, "Importing world…");',
    'actionStatus.setText("Your source file is safe. Select a dimension and a chunk rectangle.");': 'actionStatus.setText("World imported.");',
    'setBusy(true, "Scanning and removing selected chunk records…");': 'setBusy(true, "Removing selected chunks…");',
    'setBusy(true, "Packing the edited world into a .mcworld file…");': 'setBusy(true, "Exporting world…");',
    'actionStatus.setText("Export complete. Open the saved .mcworld file with Minecraft to import it.");': 'actionStatus.setText("Export complete.");',
    'toast("World exported successfully.");': 'toast("World exported.");',
    'setBusy(true, "Restoring the original working copy…");': 'setBusy(true, "Restoring original copy…");',
    'actionStatus.setText("Restored. No chunks have been pruned in this working copy.");': 'actionStatus.setText("Original copy restored.");',
    'actionStatus.setText("Previous working copy restored. Continue selecting or export it.");': 'actionStatus.setText("Working copy restored.");',
    'previewStatus.setText(detailedAlreadyCached\n                    ? "Showing cached preview…"\n                    : "Showing quick map · loading block detail in background…");': 'previewStatus.setText(detailedAlreadyCached\n                    ? "Preview ready"\n                    : "Loading terrain detail…");',
    'else previewStatus.setText(String.format(\n                                "Showing quick map · %,d chunk columns · loading block detail…", cached.getChunkCount()));': 'else previewStatus.setText(String.format(\n                                "%,d chunk columns · Loading terrain…", cached.getChunkCount()));',
    'previewStatus.setText("Reading the world database once and preparing all dimensions…");': 'previewStatus.setText("Loading preview…");',
    '"Reading world database · %,d chunk columns found…"': '"%,d chunk columns found…"',
    'previewStatus.setText("No saved chunk columns were found in this dimension.");': 'previewStatus.setText("No chunks in this dimension.");',
    '"%,d saved chunk columns · stored biome/height data · approximate terrain colours · drag to select"': '"%,d chunk columns"',
    '"%,d saved chunk columns · showing block terrain and chunk coverage"': '"%,d chunk columns"',
}
for old, new in replacements.items():
    main = replace_once(main, old, new, "copy replacement: " + old[:60])

# Show preview status only once a world is available, then keep it as live status.
main = replace_once(main,
    '''    private void loadWorldPreview() {
        if (!worldLoaded || mapView == null) return;
        final int requestId = ++previewRequestId;
''',
    '''    private void loadWorldPreview() {
        if (!worldLoaded || mapView == null) return;
        previewStatus.setVisibility(View.VISIBLE);
        final int requestId = ++previewRequestId;
''', "preview status visibility")

# Simplify the confirmation text without weakening its scope/safety information.
old_dialog = '''        String cleanupSummary = removeSavedData
                ? "\\n\\nSaved-data cleanup: ON\\nSaved mobs, entities and dropped items (legacy and modern Bedrock actor storage) plus tile entities in these chunk positions will also be removed."
                : "\\n\\nSaved-data cleanup: OFF\\nMobs, entities, dropped items and tile-entity records will be left at these pruned chunk positions. They may become orphaned data.";
        String details = "Dimension: " + dimensionName
                + "\\nChunk X: " + selectionMinX + " through " + selectionMaxX
                + "\\nChunk Z: " + selectionMinZ + " through " + selectionMaxZ
                + "\\nRectangle size: " + String.format("%,d", columns) + " chunk positions"
                + cleanupSummary
                + "\\n\\nAll other dimensions and chunks outside this rectangle are kept. Dedicated player save records are not removed. The imported .mcworld file and protected original copy are not changed.";
'''
new_dialog = '''        String cleanupSummary = removeSavedData
                ? "\\n\\nEntity and block-entity cleanup: On"
                : "\\n\\nEntity and block-entity cleanup: Off (records may become orphaned)";
        String details = "Dimension: " + dimensionName
                + "\\nChunk X: " + selectionMinX + " to " + selectionMaxX
                + "\\nChunk Z: " + selectionMinZ + " to " + selectionMaxZ
                + "\\nSize: " + String.format("%,d", columns) + " chunk positions"
                + cleanupSummary
                + "\\n\\nOther dimensions and chunks are kept. Player records are preserved. The imported file and protected original copy remain unchanged.";
'''
main = replace_once(main, old_dialog, new_dialog, "prune review dialog copy")
main = replace_once(main,
    '.setMessage("This replaces the edited working copy with the protected copy made during import. The original .mcworld file remains untouched.")',
    '.setMessage("The edited copy will be replaced with the protected original copy. The imported file remains unchanged.")',
    "restore confirmation copy")

# A map with no loaded world should not display an instructional sentence.
preview = replace_once(preview,
    'drawCentered(canvas, "Import a world to build its map preview", 13, 0xFF9DAEC3);',
    'drawCentered(canvas, "No world loaded", 13, 0xFF9DAEC3);',
    "map empty-state copy")

MAIN.write_text(main)
PREVIEW.write_text(preview)
print("Removed instructional/helper copy, simplified UI section headings and operational statuses, and retained essential validation and safety messages.")
