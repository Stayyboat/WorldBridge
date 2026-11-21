from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

replacements = {
    '''        LinearLayout selectionCard = panel();
        content.addView(selectionCard, margin(0, 0, 0, 14));
        selectionCard.addView(sectionTitle("Chunk Selection"));''':
    '''        LinearLayout selectionCard = panel();
        content.addView(selectionCard, margin(0, 0, 0, 14));
        selectionCard.setPadding(dp(15), dp(6), dp(15), dp(15));
        LinearLayout.LayoutParams selectionTitleParams = matchWrap();
        selectionTitleParams.bottomMargin = dp(6);
        selectionCard.addView(sectionTitle("Chunk Selection"), selectionTitleParams);''',
    '''        LinearLayout exportCard = panel();
        content.addView(exportCard, margin(0, 0, 0, 14));
        exportCard.addView(sectionTitle("Export"));''':
    '''        LinearLayout exportCard = panel();
        content.addView(exportCard, margin(0, 0, 0, 14));
        exportCard.setPadding(dp(15), dp(6), dp(15), dp(15));
        LinearLayout.LayoutParams exportTitleParams = matchWrap();
        exportTitleParams.bottomMargin = dp(6);
        exportCard.addView(sectionTitle("Export"), exportTitleParams);''',
}

for old, new in replacements.items():
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one exact target block, found {count}: {old.splitlines()[0]}")
    source = source.replace(old, new, 1)

if source.count('sectionTitle("Chunk Selection")') != 1 or source.count('sectionTitle("Export")') != 1:
    raise SystemExit("Target headings were not preserved exactly once.")
if source.count('selectionTitleParams.bottomMargin = dp(6);') != 1:
    raise SystemExit("Chunk Selection heading margin verification failed.")
if source.count('exportTitleParams.bottomMargin = dp(6);') != 1:
    raise SystemExit("Export heading margin verification failed.")

MAIN.write_text(source)
print("Applied compact, balanced 8dp visual gaps to Chunk Selection and Export headings only.")
