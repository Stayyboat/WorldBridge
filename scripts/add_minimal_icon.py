from pathlib import Path
import xml.etree.ElementTree as ET

root = Path("app/src/main")
res = root / "res"
(res / "drawable").mkdir(parents=True, exist_ok=True)
(res / "values").mkdir(parents=True, exist_ok=True)
(res / "mipmap-anydpi-v26").mkdir(parents=True, exist_ok=True)

# Quiet, flat mark: four chunk tiles, one purple tile, no gradients, rings,
# map pins, textures, shadows or decorative effects.
foreground = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#A78BFA" android:pathData="M23,23h25a3,3 0,0 1,3 3v25a3,3 0,0 1,-3 3H23a3,3 0,0 1,-3 -3V26a3,3 0,0 1,3 -3z"/>
    <path android:fillColor="#55515F" android:pathData="M60,23h25a3,3 0,0 1,3 3v25a3,3 0,0 1,-3 3H60a3,3 0,0 1,-3 -3V26a3,3 0,0 1,3 -3z"/>
    <path android:fillColor="#55515F" android:pathData="M23,60h25a3,3 0,0 1,3 3v25a3,3 0,0 1,-3 3H23a3,3 0,0 1,-3 -3V63a3,3 0,0 1,3 -3z"/>
    <path android:fillColor="#8B5CF6" android:pathData="M60,60h25a3,3 0,0 1,3 3v25a3,3 0,0 1,-3 3H60a3,3 0,0 1,-3 -3V63a3,3 0,0 1,3 -3z"/>
</vector>
"""
(res / "drawable" / "ic_launcher_foreground.xml").write_text(foreground)

background = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#24232B</color>
</resources>
"""
(res / "values" / "ic_launcher_background.xml").write_text(background)

adaptive = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""
(res / "mipmap-anydpi-v26" / "ic_launcher.xml").write_text(adaptive)

manifest = root / "AndroidManifest.xml"
if not manifest.exists():
    raise SystemExit("AndroidManifest.xml missing; refusing to build an icon that is not wired to the launcher.")
tree = ET.parse(manifest)
mroot = tree.getroot()
ns = "{http://schemas.android.com/apk/res/android}"
app = mroot.find("application")
if app is None:
    raise SystemExit("Manifest has no application element.")
app.set(ns + "icon", "@mipmap/ic_launcher")
app.set(ns + "roundIcon", "@mipmap/ic_launcher")
ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
tree.write(manifest, encoding="utf-8", xml_declaration=True)
print("Installed minimal four-chunk adaptive launcher icon and wired manifest.")
