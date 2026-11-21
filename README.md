# Chunkly

**Chunkly** is an Android utility for inspecting Minecraft Bedrock world chunks and pruning selected chunk areas from a separate working copy.

## Features

- Top-down world preview with chunk selection and manual chunk coordinates.
- Overworld, Nether, and End dimension views.
- Player-location indicator and End central-island/origin guides.
- Chunk pruning, with an optional **Include Entities** cleanup toggle.
- Protected original copy, restore action, and export to a new `.mcworld` file.
- Grey interface with purple selection and action accents.

The feature set is intentionally held to the v0.5.23 baseline. The 1.0 release pass focuses on stability, layout, branding, and release checks rather than adding new product capabilities.

## Safety notes

Chunkly imports the selected `.mcworld` archive into app storage and works on a separate copy. The selected source archive and Minecraft-installed world are not directly edited by the pruning workflow. Keep an independent backup before editing important worlds. Bedrock storage formats can vary between Minecraft versions, so test exported copies in Minecraft before relying on them.

## Build and QA

The GitHub Actions workflow **Build Chunkly APK** runs source-patch checks, a release preflight, and Gradle builds. It publishes:

- `Chunkly-1.0-debug-qa`: installable debug-signed APK for device testing.
- `Chunkly-1.0-release-unsigned`: release-mode APK output that still needs to be signed with the publisher's own permanent release key.
- `Chunkly-source-snapshot`: the generated Android source and release scripts used by that build.

The application ID remains `com.worldbridge.app` to preserve the identity of existing installations. Only the visible product name changes to Chunkly.

## Publishing

The unsigned release APK is not a publish-ready package. Before public distribution, configure a private release-signing key and sign the release APK (or use a signed Android App Bundle for Google Play). Keep that key and its backup secure; future updates must use the same signing identity.

## Compatibility

- Minimum Android version: Android 8.0 (API 26).
- The project targets Android API 36.
