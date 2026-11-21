from pathlib import Path

MAIN = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = MAIN.read_text()

expected = """        view.setPadding(0, dp(6), 0, dp(6));
        return view;
"""
if source.count(expected) != 1:
    raise SystemExit(
        "Expected the shared sectionTitle helper to use equal 6dp top/bottom padding."
    )
if "view.setTranslationY(-dp(3))" in source:
    raise SystemExit("A per-heading vertical offset remains; headings must share one baseline.")

print("Confirmed equal 6dp top/bottom spacing for every section heading, with no individual offsets.")
