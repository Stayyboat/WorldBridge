from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

old = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        importCard.addView(importButton, matchWrap());
'''
new = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        LinearLayout.LayoutParams importButtonParams = matchWrap();
        importButtonParams.topMargin = dp(12);
        importCard.addView(importButton, importButtonParams);
'''

count = source.count(old)
if count != 1:
    raise SystemExit(f"Expected one World import button block, found {count}")

MAIN.write_text(source.replace(old, new, 1))
print("Moved the World card import control group down by adding 12dp above the import button.")
