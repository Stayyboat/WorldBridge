from pathlib import Path

ENGINE = Path("engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java")
source = ENGINE.read_text()

anchor = '        else if (n.contains("mycelium")) color = 0xFF6A5D62;\n        else if (n.contains("podzol")) color = 0xFF9A7653;'
replacement = '''        else if (n.contains("mycelium")) color = 0xFF6A5D62;
        else if (n.contains("red_mushroom_block")) color = 0xFFB84C4C;
        else if (n.contains("brown_mushroom_block")) color = 0xFF9A6847;
        else if (n.contains("podzol")) color = 0xFF9A7653;'''

if source.count(anchor) != 1:
    raise SystemExit(f"Mushroom colour insertion point: expected exactly one match, found {source.count(anchor)}")

ENGINE.write_text(source.replace(anchor, replacement, 1))
print("Added dedicated red and brown mushroom block preview colours.")
