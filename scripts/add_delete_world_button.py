from pathlib import Path

path = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = path.read_text()


def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    source = source.replace(old, new, 1)


# Add a compact, right-aligned delete control to the World card.
replace_once(
    "    private Button importButton;\n",
    "    private Button importButton;\n    private Button deleteWorldButton;\n",
    "delete world button field",
)

replace_once(
    """        worldStatus.setPadding(0, dp(10), 0, 0);
        importCard.addView(worldStatus);

        LinearLayout settingsCard = panel();""",
    """        worldStatus.setPadding(0, dp(10), 0, 0);
        importCard.addView(worldStatus);

        LinearLayout worldActions = new LinearLayout(this);
        worldActions.setOrientation(LinearLayout.HORIZONTAL);
        worldActions.setGravity(Gravity.END);
        deleteWorldButton = actionButton("Delete world", PANEL_SOFT, TEXT);
        deleteWorldButton.setTextSize(12);
        deleteWorldButton.setPadding(dp(12), 0, dp(12), 0);
        deleteWorldButton.setMinHeight(0);
        deleteWorldButton.setMinimumHeight(dp(34));
        deleteWorldButton.setBackground(roundRect(PANEL_SOFT, dp(10), BORDER, dp(1)));
        deleteWorldButton.setOnClickListener(v -> confirmDeleteWorld());
        LinearLayout.LayoutParams deleteWorldParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(34));
        deleteWorldParams.topMargin = dp(8);
        worldActions.addView(deleteWorldButton, deleteWorldParams);
        importCard.addView(worldActions, matchWrap());

        LinearLayout settingsCard = panel();""",
    "World card delete control",
)

# Confirm exactly what is deleted; the imported source file and Minecraft's installed world are untouched.
anchor = "    private void confirmReset() {\n"
if source.count(anchor) != 1:
    raise SystemExit("Could not find the reset-confirmation method insertion point.")
methods = """    private void confirmDeleteWorld() {
        if (!worldLoaded || busy) return;
        new AlertDialog.Builder(this)
                .setTitle("Delete imported world?")
                .setMessage("This removes the imported world and its protected and working copies from WorldBridge. It does not delete the original .mcworld file you selected or any world installed in Minecraft.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Delete", (dialog, which) -> deleteImportedWorld())
                .show();
    }

    private void deleteImportedWorld() {
        if (!worldLoaded || busy) return;
        cancelPreviewWork();
        previewCache.clear();
        detailReadyDimensions.clear();
        setBusy(true, "Deleting world…");
        worker.execute(() -> {
            try {
                synchronized (worldDbLock) {
                    WorldFiles.deleteRecursively(workspace);
                }
                runOnUiThread(() -> {
                    worldLoaded = false;
                    worldName = "No world selected";
                    lastExportUri = null;
                    selectedDimension = 0;
                    selectionMinX = selectionMinZ = selectionMaxX = selectionMaxZ = 0;
                    getSharedPreferences("worldbridge", MODE_PRIVATE)
                            .edit().remove("world_name").apply();
                    if (dimensionSpinner != null) dimensionSpinner.setSelection(0);
                    if (mapView != null) {
                        mapView.setPreview(null, null);
                        mapView.setRegion(0, 0, 0, 0);
                    }
                    if (previewStatus != null) previewStatus.setVisibility(View.GONE);
                    worldStatus.setText(worldName);
                    openButton.setVisibility(View.GONE);
                    updateSelectionStatus();
                    actionStatus.setText("World deleted from WorldBridge.");
                    setBusy(false, null);
                    updateButtons();
                });
            } catch (Exception exception) {
                runOnUiThread(() -> {
                    setBusy(false, null);
                    actionStatus.setText("Delete failed: " + friendlyMessage(exception));
                    updateButtons();
                });
            }
        });
    }

"""
source = source.replace(anchor, methods + anchor, 1)

# Enable the small control only while a world is loaded and no operation is running.
replace_once(
    "        importButton.setEnabled(!busy);\n",
    "        importButton.setEnabled(!busy);\n        deleteWorldButton.setEnabled(worldLoaded && !busy);\n",
    "delete world enabled state",
)
replace_once(
    "        importButton.setAlpha(busy ? 0.55f : 1f);\n",
    "        importButton.setAlpha(busy ? 0.55f : 1f);\n        deleteWorldButton.setAlpha(worldLoaded && !busy ? 1f : 0.48f);\n",
    "delete world enabled appearance",
)

path.write_text(source)
print("Added a compact Delete world button with confirmation and safe removal of WorldBridge's private copies only.")
