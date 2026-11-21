from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

needle = '''        view.setPadding(0, 0, 0, dp(4));
        return view;
'''
replacement = '''        view.setPadding(0, 0, 0, dp(4));
        if ("World".equals(value)
                || "Prune".equals(value)
                || "Review and Prune".equals(value)
                || "Export".equals(value)) {
            view.setTranslationY(-dp(3));
        }
        return view;
'''

if source.count(needle) != 1:
    raise SystemExit(
        "Expected the shared sectionTitle padding/return block exactly once; "
        f"found {source.count(needle)}"
    )

MAIN.write_text(source.replace(needle, replacement, 1))
print("Raised only World, Prune/Review and Prune, and Export headings by 3dp.")
