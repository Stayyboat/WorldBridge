from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

world_old = """        TextView importTitle = sectionTitle("World");
        importCard.addView(importTitle);"""
dimension_old = """        settingsCard.addView(sectionTitle("Dimension"));"""

for old, new, name in (
    (world_old, '        addCardHeading(importCard, "World");', "World"),
    (dimension_old, '        addCardHeading(settingsCard, "Dimension");', "Dimension"),
):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {name} heading block, found {count}")
    source = source.replace(old, new, 1)

helper_marker = """    private TextView sectionTitle(String value) {
"""
helper = """    private void addCardHeading(LinearLayout card, String value) {
        TextView heading = sectionTitle(value);
        heading.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        heading.setTextAlignment(View.TEXT_ALIGNMENT_VIEW_START);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(28));
        params.gravity = Gravity.START;
        card.addView(heading, params);
    }

"""
if source.count(helper_marker) != 1:
    raise SystemExit("Could not find the shared heading helper insertion point")
if "private void addCardHeading(LinearLayout card, String value)" in source:
    raise SystemExit("Shared card heading helper already exists")
source = source.replace(helper_marker, helper + helper_marker, 1)

if source.count('addCardHeading(importCard, "World");') != 1:
    raise SystemExit("World title does not use the shared aligned heading helper")
if source.count('addCardHeading(settingsCard, "Dimension");') != 1:
    raise SystemExit("Dimension title does not use the shared aligned heading helper")

MAIN.write_text(source)
print("World and Dimension now use the same fixed-height, start-aligned heading row.")
