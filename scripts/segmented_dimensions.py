from pathlib import Path

p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
s = p.read_text()

field = "    private Spinner dimensionSpinner;"
if field not in s:
    raise SystemExit("Could not find dimension spinner field.")
s = s.replace(field, field + "\n    private LinearLayout dimensionTabs;\n    private TextView[] dimensionTabViews;")

old = r'''        dimensionSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (worldLoaded && !busy) loadWorldPreview();
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
        LinearLayout.LayoutParams spinnerParams = matchWrap();
        spinnerParams.topMargin = dp(10);
        settingsCard.addView(dimensionSpinner, spinnerParams);'''

new = r'''        dimensionSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                updateDimensionTabs(position);
                if (worldLoaded && !busy) loadWorldPreview();
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });

        // Keep the Spinner as the single source of selected-dimension state so all
        // existing preview, cache, and pruning logic remains unchanged.
        dimensionSpinner.setVisibility(View.GONE);
        dimensionTabs = new LinearLayout(this);
        dimensionTabs.setOrientation(LinearLayout.HORIZONTAL);
        dimensionTabs.setGravity(Gravity.CENTER);
        dimensionTabs.setPadding(dp(4), dp(4), dp(4), dp(4));
        dimensionTabs.setBackground(roundRect(PANEL_SOFT, dp(16), BORDER, dp(1)));
        dimensionTabs.setClipToOutline(true);
        dimensionTabViews = new TextView[3];
        String[] dimensionLabels = {"Overworld", "Nether", "End"};
        for (int i = 0; i < dimensionLabels.length; i++) {
            final int index = i;
            TextView tab = label(dimensionLabels[i], 13, MUTED, true);
            tab.setGravity(Gravity.CENTER);
            tab.setSingleLine(true);
            tab.setIncludeFontPadding(false);
            tab.setFocusable(true);
            tab.setClickable(true);
            tab.setPadding(dp(3), dp(11), dp(3), dp(11));
            tab.setOnClickListener(v -> {
                if (dimensionSpinner.getSelectedItemPosition() != index) {
                    dimensionSpinner.setSelection(index);
                } else {
                    tab.animate().scaleX(0.96f).scaleY(0.96f).setDuration(75)
                            .withEndAction(() -> tab.animate().scaleX(1f).scaleY(1f).setDuration(120).start()).start();
                }
            });
            dimensionTabViews[i] = tab;
            LinearLayout.LayoutParams tabParams = new LinearLayout.LayoutParams(0, dp(44), 1f);
            if (i > 0) tabParams.leftMargin = dp(3);
            dimensionTabs.addView(tab, tabParams);
        }
        LinearLayout.LayoutParams tabsParams = matchWrap();
        tabsParams.topMargin = dp(12);
        settingsCard.addView(dimensionTabs, tabsParams);
        updateDimensionTabs(dimensionSpinner.getSelectedItemPosition());'''

if old not in s:
    raise SystemExit("Could not find original Spinner UI block.")
s = s.replace(old, new)

anchor = "    private View buildBottomNavigation() {"
if anchor not in s:
    raise SystemExit("Could not find helper insertion point.")
helper = r'''    private void updateDimensionTabs(int selectedIndex) {
        if (dimensionTabViews == null) return;
        for (int i = 0; i < dimensionTabViews.length; i++) {
            TextView tab = dimensionTabViews[i];
            if (tab == null) continue;
            boolean selected = i == selectedIndex;
            tab.setTextColor(selected ? 0xFFF4EEFF : MUTED);
            tab.setBackground(roundRect(
                    selected ? 0xFF49366F : 0x002D2D36,
                    dp(12),
                    selected ? ACCENT : 0x002D2D36,
                    selected ? dp(1) : 0));
            tab.animate().scaleX(selected ? 1f : 0.98f)
                    .scaleY(selected ? 1f : 0.98f)
                    .setDuration(170)
                    .setInterpolator(new android.view.animation.DecelerateInterpolator())
                    .start();
        }
    }

'''
s = s.replace(anchor, helper + anchor)

p.write_text(s)
print("Replaced the visible dimension dropdown with an animated Overworld / Nether / End segmented control.")
