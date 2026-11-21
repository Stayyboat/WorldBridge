from pathlib import Path

ENGINE = Path("engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java")
source = ENGINE.read_text()

old = '        else if (n.contains("podzol") || n.contains("mycelium")) color = 0xFF79604F;'
new = '''        else if (n.contains("mycelium")) color = 0xFF6A5D62;
        else if (n.contains("podzol")) color = 0xFF9A7653;'''

count = source.count(old)
if count != 1:
    raise SystemExit(f"Mycelium colour rule: expected exactly one match, found {count}")

ENGINE.write_text(source.replace(old, new, 1))
print("Applied a dedicated grey-mauve Mycelium top colour; Podzol keeps its earthy brown colour.")
