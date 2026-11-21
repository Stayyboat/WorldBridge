from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path('.')
MAIN = ROOT / 'app/src/main/java/com/worldbridge/app/MainActivity.java'
PREVIEW = ROOT / 'app/src/main/java/com/worldbridge/app/WorldPreviewView.java'
ENGINE_PREVIEW = ROOT / 'engine/src/main/java/com/worldbridge/engine/BedrockWorldPreview.java'
PRUNER = ROOT / 'engine/src/main/java/com/worldbridge/engine/BedrockChunkPruner.java'
FILES = ROOT / 'app/src/main/java/com/worldbridge/app/WorldFiles.java'
GRADLE = ROOT / 'app/build.gradle.kts'
MANIFEST = ROOT / 'app/src/main/AndroidManifest.xml'
ANDROID = '{http://schemas.android.com/apk/res/android}'


def require(condition, message):
    if not condition:
        raise SystemExit('RELEASE PREFLIGHT FAILED: ' + message)


main = MAIN.read_text()
preview = PREVIEW.read_text()
engine = ENGINE_PREVIEW.read_text()
pruner = PRUNER.read_text()
files = FILES.read_text()
gradle = GRADLE.read_text()
manifest = ET.parse(MANIFEST).getroot()
app = manifest.find('application')
require(app is not None, 'manifest application element is missing')

# Preserve the package ID so this is an in-place update of existing installs.
require('applicationId = "com.worldbridge.app"' in gradle,
        'applicationId changed; existing installs/data would not upgrade safely')
require('versionCode = 52' in gradle and 'versionName = "1.0"' in gradle,
        'version must be code 52 / name 1.0')
require(app.get(ANDROID + 'label') == 'Chunkly', 'application label is not Chunkly')
launcher_labels = []
for node in manifest.iter():
    if node.tag in ('activity', 'activity-alias'):
        for intent_filter in node.findall('intent-filter'):
            actions = [c.get(ANDROID + 'name') for c in list(intent_filter) if c.tag == 'action']
            categories = [c.get(ANDROID + 'name') for c in list(intent_filter) if c.tag == 'category']
            if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in categories:
                launcher_labels.append(node.get(ANDROID + 'label', app.get(ANDROID + 'label')))
require(launcher_labels and all(x == 'Chunkly' for x in launcher_labels),
        'launcher activity does not display Chunkly')
require('label("Chunkly", 30' in main and 'setTitle("Chunkly")' in main,
        'main screen branding is incomplete')

# World card: real layout row, ellipsized name, no old translation overlap.
require('worldStatus.setEllipsize(TextUtils.TruncateAt.END)' in main,
        'world name is not safely ellipsized')
require('worldActions.setGravity(Gravity.CENTER_VERTICAL)' in main,
        'world status and Delete button are not vertically aligned')
require('importButton.setTranslationY' not in main,
        'old World import translation overlap remains')
require('dimensionSpinner' not in main and 'Spinner' not in main,
        'unused hidden dimension spinner remains')

# Typography, edge insets, gesture safety, balanced heading spacing, and theme consistency.
require('view.setPadding(0, dp(2), 0, dp(2));' in main,
        'section headings do not have equal 2dp top/bottom spacing')
require('selectionCard.setPadding(dp(15), dp(6), dp(15), dp(15));' in main
        and 'selectionTitleParams.bottomMargin = dp(6);' in main,
        'Chunk Selection heading spacing is not compact and balanced')
require('exportCard.setPadding(dp(15), dp(6), dp(15), dp(15));' in main
        and 'exportTitleParams.bottomMargin = dp(6);' in main,
        'Export heading spacing is not compact and balanced')
require('importCard.setPadding(dp(15), dp(6), dp(15), dp(15));' in main,
        'World card top inset is not reduced to 6dp')
require('settingsCard.setPadding(dp(15), dp(6), dp(15), dp(15));' in main,
        'Dimension card top inset is not reduced to 6dp')
require('addCardHeading(importCard, "World");' in main
        and 'addCardHeading(settingsCard, "Dimension");' in main,
        'World and Dimension do not use the shared aligned heading row')
require('heading.setTranslationY(2f);' in main,
        'World and Dimension headings are not shifted down exactly 2 physical pixels')
require('ViewGroup.LayoutParams.MATCH_PARENT, dp(28)' in main
        and 'heading.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);' in main,
        'World and Dimension heading rows are not identically aligned')
require('view.setTranslationY(-dp(3))' not in main,
        'per-heading vertical offsets are still uneven')
require('WindowInsets.Type.systemBars()' in main and 'WindowInsets.Type.ime()' in main,
        'system-bar / keyboard inset handling is missing')
require('setIncludeFontPadding(false)' in main and 'button.setGravity(Gravity.CENTER)' in main,
        'consistent text metrics/button alignment are missing')
require('selectionFill = 0x55B69CFF' in preview and 'selectionStroke = 0xFFB69CFF' in preview,
        'selection colour is not using the purple accent')
require('private void requestParentIntercept(boolean disallow)' in preview,
        'safe touch-parent helper is missing')
require('getParent().requestDisallowInterceptTouchEvent' not in preview,
        'unsafe direct parent touch call remains')
require('preview.dimensionId == 0 ? 128f : 64f' in preview,
        'Overworld-specific 128x zoom cap is missing')
require('Math.min(baseScale * maxZoom, scale * detector.getScaleFactor())' in preview,
        'dimension-aware zoom clamp is missing')
require('Math.min(baseScale * 64f, scale * detector.getScaleFactor())' not in preview,
        'old shared 64x preview zoom cap remains')

# Confirm all existing capabilities from the frozen v0.5.23 feature set remain.
for label in ('Overworld', 'Nether', 'End', 'Include Entities', 'Delete world',
              'Export .mcworld', 'Restore original copy'):
    require(label in main, f'required existing UI feature missing: {label}')
require('removeSavedData' in pruner and 'ACTOR_DIGEST_PREFIX' in pruner,
        'saved entities cleanup path is missing')
require('withoutRegion' in engine and 'drawPlayerMarker' in preview
        and 'drawEndOriginMarker' in preview,
        'player marker / End origin marker source appears incomplete')
require('endIslandColorAtBlock' not in preview and 'islandColorAtBlock' not in preview,
        'synthetic End island overlay is still present')
for token in ('red_mushroom_block', 'brown_mushroom_block', '0xFF6A5D62', '0xFF9A7653'):
    require(token in engine, f'expected block palette rule missing: {token}')
require('0xFFB84C4C' in engine and '0xFF9A6847' in engine,
        'mushroom block preview colours are missing')

# Import safety and accurate pruning counters.
require('MAX_UNPACKED_BYTES' in files and 'copied > MAX_UNPACKED_BYTES' in files,
        'compressed archive size cap is missing')
require('selectedChunkColumns' in pruner and 'database.get(actorKey) != null' in pruner,
        'pruner count accuracy checks are missing')
require('if (recordCount > 0) database.compactRange(null, null)' in pruner,
        'empty-selection compaction guard is missing')

# Confirm all generated launcher bitmap densities are present.
for density in ('mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi', 'nodpi'):
    require((ROOT / f'app/src/main/res/mipmap-{density}/ic_launcher.png').is_file(),
            f'launcher icon missing for {density}')

print('Chunkly 1.0 release preflight passed: identity, branding, World layout, balanced section-heading spacing, UI metrics, insets, palette, feature-preservation markers, import caps, pruning accounting, and launcher assets.');
