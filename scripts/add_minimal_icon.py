from pathlib import Path
import math
import struct
import zlib
import xml.etree.ElementTree as ET

ROOT = Path("app/src/main")
RES = ROOT / "res"
ANDROID = "{http://schemas.android.com/apk/res/android}"

# Flat, minimal chunk-grid mark on the existing charcoal/purple palette.
BG = (0x24, 0x23, 0x2B, 255)
TILES = [
    (0xA7, 0x8B, 0xFA, 255),
    (0x55, 0x51, 0x5F, 255),
    (0x55, 0x51, 0x5F, 255),
    (0x8B, 0x5C, 0xF6, 255),
]


def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def make_icon_png(size):
    # Keep the complete four-tile mark comfortably inside launcher masking.
    pixels = bytearray()
    margin = round(size * 0.185)
    gap = round(size * 0.075)
    tile = round(size * 0.295)
    radius = max(1, round(size * 0.028))
    boxes = [
        (margin, margin, margin + tile, margin + tile, TILES[0]),
        (margin + tile + gap, margin, margin + tile * 2 + gap, margin + tile, TILES[1]),
        (margin, margin + tile + gap, margin + tile, margin + tile * 2 + gap, TILES[2]),
        (margin + tile + gap, margin + tile + gap, margin + tile * 2 + gap, margin + tile * 2 + gap, TILES[3]),
    ]

    for y in range(size):
        pixels.append(0)  # PNG filter: None
        for x in range(size):
            color = BG
            for x0, y0, x1, y1, tile_color in boxes:
                if x0 <= x < x1 and y0 <= y < y1:
                    # Rounded corners without extra libraries or platform tools.
                    cx = min(max(x, x0 + radius), x1 - radius - 1)
                    cy = min(max(y, y0 + radius), y1 - radius - 1)
                    dx, dy = x - cx, y - cy
                    if dx * dx + dy * dy <= radius * radius:
                        color = tile_color
                        break
            pixels.extend(color)

    header = struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
        + png_chunk(b"IEND", b"")
    )


if not (ROOT / "AndroidManifest.xml").exists():
    raise SystemExit("AndroidManifest.xml missing; refusing to build an unreferenced launcher icon.")

# Create regular bitmap launcher resources at every Android launcher density.
# Bitmap resources are deliberately used here instead of relying only on adaptive
# XML resources, which some launchers/installer flows can continue to cache or skip.
density_sizes = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
for folder, size in density_sizes.items():
    out = RES / folder
    out.mkdir(parents=True, exist_ok=True)
    png = make_icon_png(size)
    (out / "ic_launcher.png").write_bytes(png)
    (out / "ic_launcher_round.png").write_bytes(png)

# A high-resolution no-density copy is useful to tooling that requests it directly.
nodpi = RES / "mipmap-nodpi"
nodpi.mkdir(parents=True, exist_ok=True)
png = make_icon_png(512)
(nodpi / "ic_launcher.png").write_bytes(png)
(nodpi / "ic_launcher_round.png").write_bytes(png)

# Remove the previous adaptive-only resource so @mipmap/ic_launcher resolves to
# the new explicit density bitmaps on every Android release, including Android 8+.
for old_name in ("ic_launcher.xml", "ic_launcher_round.xml"):
    old = RES / "mipmap-anydpi-v26" / old_name
    if old.exists():
        old.unlink()

manifest = ROOT / "AndroidManifest.xml"
tree = ET.parse(manifest)
root = tree.getroot()
app = root.find("application")
if app is None:
    raise SystemExit("Manifest has no application element.")

app.set(ANDROID + "icon", "@mipmap/ic_launcher")
app.set(ANDROID + "roundIcon", "@mipmap/ic_launcher_round")

# An activity-level icon overrides the application icon. Explicitly set the
# launcher activity (and launcher aliases, if present) as well.
launcher_count = 0
for node in root.iter():
    if node.tag not in ("activity", "activity-alias"):
        continue
    is_launcher = False
    for intent_filter in node.findall("intent-filter"):
        has_main = any(
            child.tag == "action" and child.get(ANDROID + "name") == "android.intent.action.MAIN"
            for child in list(intent_filter)
        )
        has_launcher = any(
            child.tag == "category" and child.get(ANDROID + "name") == "android.intent.category.LAUNCHER"
            for child in list(intent_filter)
        )
        if has_main and has_launcher:
            is_launcher = True
            break
    if is_launcher:
        node.set(ANDROID + "icon", "@mipmap/ic_launcher")
        node.set(ANDROID + "roundIcon", "@mipmap/ic_launcher_round")
        launcher_count += 1

ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
tree.write(manifest, encoding="utf-8", xml_declaration=True)
if launcher_count == 0:
    print("Warning: no MAIN/LAUNCHER activity found; application icon was updated.")
print(f"Installed bitmap launcher icons in {len(density_sizes)} densities and updated {launcher_count} launcher component(s).")
