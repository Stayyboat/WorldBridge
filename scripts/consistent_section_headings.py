from pathlib import Path

path = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = path.read_text()

replacements = {
    'TextView importTitle = label("World", 17, TEXT, true);':
        'TextView importTitle = sectionTitle("World");',
    'settingsCard.addView(label("Dimension", 17, TEXT, true));':
        'settingsCard.addView(sectionTitle("Dimension"));',
    'selectionCard.addView(label("Chunk selection", 17, TEXT, true));':
        'selectionCard.addView(sectionTitle("Chunk Selection"));',
    'actionCard.addView(label("Prune", 17, TEXT, true));':
        'actionCard.addView(sectionTitle("Prune"));',
    'exportCard.addView(label("Export", 17, TEXT, true));':
        'exportCard.addView(sectionTitle("Export"));',
}

for old, new in replacements.items():
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one heading occurrence for {old!r}, found {count}")
    source = source.replace(old, new, 1)

needle = '    private TextView label(String value, int size, int color, boolean bold) {\n'
method = '''    private TextView sectionTitle(String value) {
        TextView view = label(value, 17, TEXT, true);
        view.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        view.setIncludeFontPadding(false);
        view.setLetterSpacing(0.01f);
        view.setPadding(0, 0, 0, dp(4));
        return view;
    }

'''
if source.count(needle) != 1:
    raise SystemExit("Could not find the label helper insertion point exactly once")
source = source.replace(needle, method + needle, 1)

path.write_text(source)
print("Applied one shared section-heading style to World, Dimension, Chunk Selection, Prune and Export.")
