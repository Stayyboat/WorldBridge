from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

# Match the compact top inset already used by Chunk Selection and Export.
# Keep the existing bottom inset and horizontal card insets unchanged.
for card_name, label in (("importCard", "World"), ("settingsCard", "Dimension")):
    marker = f'        LinearLayout {card_name} = panel();\n'
    if source.count(marker) != 1:
        raise SystemExit(f"Could not identify the {label} card exactly once")
    target = marker + f'        content.addView({card_name}, margin(0, 0, 0, 14));\n'
    replacement = target + f'        {card_name}.setPadding(dp(15), dp(6), dp(15), dp(15));\n'
    if source.count(target) != 1:
        raise SystemExit(f"Could not identify the {label} card attachment exactly once")
    if replacement in source:
        raise SystemExit(f"{label} card top inset is already adjusted")
    source = source.replace(target, replacement, 1)

if source.count('importCard.setPadding(dp(15), dp(6), dp(15), dp(15));') != 1:
    raise SystemExit("World card top inset change did not apply")
if source.count('settingsCard.setPadding(dp(15), dp(6), dp(15), dp(15));') != 1:
    raise SystemExit("Dimension card top inset change did not apply")

MAIN.write_text(source)
print("Reduced only the top inset of World and Dimension cards from 15dp to 6dp.")
