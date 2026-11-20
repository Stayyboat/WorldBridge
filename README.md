# WorldBridge

Android utility for previewing Minecraft Bedrock world chunks and exporting a copy with selected chunk columns removed.

## Build

The GitHub Actions workflow **Build WorldBridge APK** builds a debug APK and publishes it as an Actions artifact.

Upload the project files from the `WorldBridgeAndroid-preview-source.zip` archive to the repository root (keep the folder structure). Then open **Actions → Build WorldBridge APK → Run workflow**. Download the `WorldBridge-debug-apk` artifact from the completed run.

The original world is intended to remain untouched; the app works on a separate copy. Preview parsing and pruning still require validation against real Bedrock worlds before relying on it for important saves.
