from pathlib import Path
import struct
import zlib
import xml.etree.ElementTree as ET

ROOT = Path("app/src/main")
RES = ROOT / "res"
ANDROID = "{http://schemas.android.com/apk/res/android}"

# Minimal chunk-grid mark. Matching purple tiles and matching grey tiles keep
# the pattern balanced; all four tile dimensions and all four outer margins
# are generated from one centred grid calculation.
BG = (0x24, 0x23, 0x2B, 255)
PURPLE = (0x8B, 0x5C, 0xF6, 255)
GREY = (0x55, 0x51, 0x5F, 255)
TILES = (PURPLE, GREY, GREY, PURPLE)


def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def make_icon_png(size):
    pixels = bytearray()

    # A centred square grid with equal-width tiles, one equal gap, and
    # mathematically equal margins on all four sides.
    tile = size * 0.30
    gap = size * 0.075
    grid_size = tile * 2 + gap
    margin = (size - grid_size) / 2.0
    radius = size * 0.028

    left = margin
    middle = margin + tile
    right = middle + gap
    bottom = margin + tile * 2 + gap

    boxes = (
        (left, margin, middle, margin + tile, TILES[0]),
        (right, margin, right + tile, margin + tile, TILES[1]),
        (left, margin + tile + gap, middle, bottom, TILES[2]),
        (right, margin + tile + gap, right + tile, bottom, TILES[3]),
    )

    for y in range(size):
        py = y + 0.5
        pixels.append(0)  # PNG filter: None
        for x in range(size):
            px = x + 0.5
            color = BG

            for x0, y0, x1, y1, tile_color in boxes:
                if x0 <= px < x1 and y0 <= py < y1:
                    # Pixel-centre rounded-rectangle test. Using continuous
                    # coordinates makes opposite edges exact mirror images.
                    cx = min(max(px, x0 + radius), x1 - radius)
                    cy = min(max(py, y0 + radius), y1 - radius)
                    dx = px - cx
                    dy = py - cy
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

nodpi = RES / "mipmap-nodpi"
nodpi.mkdir(parents=True, exist_ok=True)
png = make_icon_png(512)
(nodpi / "ic_launcher.png").write_bytes(png)
(nodpi / "ic_launcher_round.png").write_bytes(png)

# Avoid adaptive-only fallback resources; use the explicit bitmaps above.
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
print(f"Generated perfectly centred, symmetrical chunk-grid icons in {len(density_sizes)} densities; updated {launcher_count} launcher component(s).")
