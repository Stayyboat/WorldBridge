from pathlib import Path
p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
s = p.read_text()

# Make the entire visible tab area explicitly touch-responsive, not just its text.
old = '''            tab.setOnClickListener(v -> selectDimension(index));
            dimensionTabViews[i] = tab;'''
new = '''            tab.setOnClickListener(v -> selectDimension(index));
            tab.setOnTouchListener((v, event) -> {
                if (event.getActionMasked() == android.view.MotionEvent.ACTION_UP) {
                    v.performClick();
                    return true;
                }
                return event.getActionMasked() == android.view.MotionEvent.ACTION_DOWN
                        || event.getActionMasked() == android.view.MotionEvent.ACTION_MOVE;
            });
            dimensionTabViews[i] = tab;'''
if old not in s:
    raise SystemExit("Expected dimension tab click block not found.")
s = s.replace(old, new)

# Parent surface is clickable as well and routes taps to the correct third.
old = '''        settingsCard.addView(dimensionTabs, tabsParams);
        updateDimensionTabs(selectedDimension);'''
new = '''        settingsCard.addView(dimensionTabs, tabsParams);
        dimensionTabs.setClickable(true);
        dimensionTabs.setOnTouchListener((view, event) -> {
            if (event.getActionMasked() != android.view.MotionEvent.ACTION_UP) return true;
            float segmentWidth = dimensionTabs.getWidth() / 3f;
            int tappedIndex = Math.max(0, Math.min(2, (int) (event.getX() / Math.max(1f, segmentWidth))));
            if (tappedIndex >= 0 && tappedIndex < dimensionTabViews.length) {
                dimensionTabViews[tappedIndex].performClick();
            }
            return true;
        });
        updateDimensionTabs(selectedDimension);'''
if old not in s:
    raise SystemExit("Expected dimension tabs container block not found.")
s = s.replace(old, new)

# Never silently ignore the interaction while a world operation is busy.
old = '''    private void selectDimension(int index) {
        if (index < 0 || index > 2 || index == selectedDimension || busy) return;
        selectedDimension = index;'''
new = '''    private void selectDimension(int index) {
        if (index < 0 || index > 2 || index == selectedDimension) return;
        if (busy) {
            toast("Please wait for the current world operation to finish.");
            return;
        }
        if (!worldLoaded) {
            toast("Import a world before choosing a dimension.");
            updateDimensionTabs(selectedDimension);
            return;
        }
        selectedDimension = index;'''
if old not in s:
    raise SystemExit("Expected selectDimension method not found.")
s = s.replace(old, new)

# Make the controls' enabled state and accessibility reflect whether a world is ready.
old = '''            tab.setTextColor(selected ? 0xFFF4EEFF : MUTED);
            tab.setBackground(roundRect('''
new = '''            tab.setEnabled(worldLoaded && !busy);
            tab.setClickable(true);
            tab.setContentDescription(new String[]{"Overworld", "Nether", "End"}[i]
                    + (selected ? ", selected dimension" : ", switch dimension"));
            tab.setAlpha(worldLoaded && !busy ? 1f : 0.58f);
            tab.setTextColor(selected ? 0xFFF4EEFF : MUTED);
            tab.setBackground(roundRect('''
if old not in s:
    raise SystemExit("Expected updateDimensionTabs styling block not found.")
s = s.replace(old, new)

p.write_text(s)
print("Made dimension tabs touch-responsive with parent hit-target support, explicit busy feedback and accessible selected state.")

# Re-enable/disable dimension tabs whenever world load or busy state changes.
old = '''        resetButton.setAlpha(worldLoaded && !busy ? 1f : 0.48f);
    }

    private String friendlyMessage'''
new = '''        resetButton.setAlpha(worldLoaded && !busy ? 1f : 0.48f);
        // Tabs start disabled before a world exists; refresh their state after import,
        // workspace restore, and every operation that toggles busy.
        updateDimensionTabs(selectedDimension);
    }

    private String friendlyMessage'''
if old not in s:
    raise SystemExit("Could not find updateButtons block for the dimension-tab state refresh.")
s = s.replace(old, new)
