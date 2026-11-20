from pathlib import Path

p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
s = p.read_text()

# The hidden Spinner was still being used as the source of truth. On some Android
# builds its selection callback does not fire reliably when it is GONE. Make the
# visible tabs own the dimension state directly.
s = s.replace("    private Spinner dimensionSpinner;\n", "    private Spinner dimensionSpinner;\n    private int selectedDimension = 0;\n")

old_listener = '''        dimensionSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                updateDimensionTabs(position);
                if (worldLoaded && !busy) loadWorldPreview();
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });'''
if old_listener in s:
    s = s.replace(old_listener, '''        dimensionSpinner.setOnItemSelectedListener(null);''')

old_click = '''            tab.setOnClickListener(v -> {
                if (dimensionSpinner.getSelectedItemPosition() != index) {
                    dimensionSpinner.setSelection(index);
                } else {
                    tab.animate().scaleX(0.96f).scaleY(0.96f).setDuration(75)
                            .withEndAction(() -> tab.animate().scaleX(1f).scaleY(1f).setDuration(120).start()).start();
                }
            });'''
new_click = '''            tab.setOnClickListener(v -> selectDimension(index));'''
if old_click not in s:
    raise SystemExit("Dimension tab click handler not found; refusing to patch an unexpected source.")
s = s.replace(old_click, new_click)

s = s.replace("updateDimensionTabs(dimensionSpinner.getSelectedItemPosition());",
              "updateDimensionTabs(selectedDimension);")
s = s.replace("int dimensionIndex = dimensionSpinner.getSelectedItemPosition();",
              "int dimensionIndex = selectedDimension;")
s = s.replace("final int dimensionId = dimensionSpinner.getSelectedItemPosition();",
              "final int dimensionId = selectedDimension;")

anchor = "    private void updateDimensionTabs(int selectedIndex) {"
if anchor not in s:
    raise SystemExit("Dimension tab update method not found.")
helper = '''    private void selectDimension(int index) {
        if (index < 0 || index > 2 || index == selectedDimension || busy) return;
        selectedDimension = index;
        if (dimensionSpinner != null) dimensionSpinner.setSelection(index);
        updateDimensionTabs(index);
        cancelPreviewWork();
        if (mapView != null) {
            mapView.setPreview(null, null);
            mapView.setRegion(selectionMinX, selectionMinZ, selectionMaxX, selectionMaxZ);
        }
        if (worldLoaded) loadWorldPreview();
    }

'''
s = s.replace(anchor, helper + anchor)
p.write_text(s)
print("Fixed dimension selection: visible tabs now own the state, update the highlight, cancel stale scans, and load the chosen dimension directly.")
