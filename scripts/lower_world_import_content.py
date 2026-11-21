from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

old = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        importCard.addView(importButton, matchWrap());
        worldStatus = label(worldName, 13, MUTED, false);
        worldStatus.setPadding(0, dp(10), 0, 0);
        importCard.addView(worldStatus);

        LinearLayout worldActions = new LinearLayout(this);
'''
new = '''        importButton = actionButton("Import .mcworld", ACCENT, BG);
        importButton.setOnClickListener(v -> chooseWorld());
        importCard.addView(importButton, matchWrap());
        importButton.setTranslationY(dp(12));
        worldStatus = label(worldName, 13, MUTED, false);
        worldStatus.setPadding(0, dp(10), 0, 0);
        importCard.addView(worldStatus);
        worldStatus.setTranslationY(dp(12));

        LinearLayout worldActions = new LinearLayout(this);
'''
if source.count(old) != 1:
    raise SystemExit(f"Expected the World import/status block exactly once, found {source.count(old)}")
source = source.replace(old, new, 1)

needle = '''        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, matchWrap());
'''
replacement = '''        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, matchWrap());
        worldActions.setTranslationY(dp(12));
'''
if source.count(needle) != 1:
    raise SystemExit(f"Expected the World actions row exactly once, found {source.count(needle)}")
source = source.replace(needle, replacement, 1)

MAIN.write_text(source)
print("Shifted only the World import button, world status, and Delete world row down by 12dp without resizing the card.")
