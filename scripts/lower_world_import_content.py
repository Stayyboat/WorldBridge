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
    raise SystemExit(f"Expected the base World import/status block exactly once, found {source.count(old)}")
source = source.replace(old, new, 1)

needle = '''        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, matchWrap());
'''
if source.count(needle) != 1:
    raise SystemExit(f"Expected the Delete world row exactly once, found {source.count(needle)}")
# Leave worldActions at its original position so Delete world sits 12dp higher than before.
MAIN.write_text(source)
print("Kept the Import button and status lowered by 12dp; restored Delete world row to its original vertical position.")
