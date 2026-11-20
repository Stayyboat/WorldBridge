from pathlib import Path

p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
s = p.read_text()

# Dark emerald palette.
s = s.replace("private static final int BG = 0xFF0A1220;", "private static final int BG = 0xFF071710;")
s = s.replace("private static final int PANEL = 0xFF121F32;", "private static final int PANEL = 0xFF10251C;")
s = s.replace("private static final int PANEL_SOFT = 0xFF17263B;", "private static final int PANEL_SOFT = 0xFF183428;")
s = s.replace("private static final int ACCENT = 0xFF7CE0A4;", "private static final int ACCENT = 0xFF70E2A0;")
s = s.replace("private static final int TEXT = 0xFFEAF1FA;", "private static final int TEXT = 0xFFE8F5EC;")
s = s.replace("private static final int MUTED = 0xFF9DAEC3;", "private static final int MUTED = 0xFF9BB8A6;")
s = s.replace("private static final int BG = 0xFF071710;", "private static final int BG = 0xFF071710;\n    private static final int NAV_BG = 0xFF0C2017;\n    private static final int BORDER = 0xFF244A35;")

s = s.replace("    private ProgressBar progressBar;", """    private ProgressBar progressBar;
    private ScrollView mainScroll;
    private View homeAnchor;
    private View editorAnchor;
    private View exportAnchor;
    private TextView navHome;
    private TextView navEditor;
    private TextView navExport;""")

s = s.replace("""        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);""", """        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

        ScrollView scroll = new ScrollView(this);
        mainScroll = scroll;
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        scroll.setBackgroundColor(BG);""")

s = s.replace("""        LinearLayout importCard = panel();
        content.addView(importCard, margin(0, 0, 0, 14));""", """        LinearLayout importCard = panel();
        homeAnchor = importCard;
        content.addView(importCard, margin(0, 0, 0, 14));""")
s = s.replace("""        LinearLayout selectionCard = panel();
        content.addView(selectionCard, margin(0, 0, 0, 14));""", """        LinearLayout selectionCard = panel();
        editorAnchor = selectionCard;
        content.addView(selectionCard, margin(0, 0, 0, 14));""")
s = s.replace("""        LinearLayout exportCard = panel();
        content.addView(exportCard, margin(0, 0, 0, 14));""", """        LinearLayout exportCard = panel();
        exportAnchor = exportCard;
        content.addView(exportCard, margin(0, 0, 0, 14));""")

s = s.replace("""        setContentView(scroll);
        syncManualInputs();""", """        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        root.addView(buildBottomNavigation(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(66)));
        setContentView(root);
        animateCards(content);
        syncManualInputs();""")

# Consistent emerald surfaces, larger radii and calmer borders.
s = s.replace("layout.setBackground(roundRect(PANEL, dp(16), 0xFF22334A, dp(1)));",
              "layout.setBackground(roundRect(PANEL, dp(19), BORDER, dp(1)));")
s = s.replace("button.setBackground(roundRect(background, dp(11), background, 0));",
              "button.setBackground(roundRect(background, dp(14), background, 0));")
s = s.replace("roundRect(selected ? ACCENT : PANEL_SOFT, dp(9), selected ? ACCENT : 0xFF30435C, dp(1))",
              "roundRect(selected ? ACCENT : PANEL_SOFT, dp(12), selected ? ACCENT : BORDER, dp(1))")
s = s.replace("roundRect(PANEL_SOFT, dp(10), 0xFF30435C, dp(1))",
              "roundRect(PANEL_SOFT, dp(12), BORDER, dp(1))")
s = s.replace("0xFF243851, TEXT", "0xFF1B3B2B, TEXT")

# Navigation scrolls to the existing workflow sections; all existing actions remain in place.
insert_at = s.index("    private LinearLayout coordinateRow(boolean minimumRow) {")
nav_methods = r'''    private View buildBottomNavigation() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER);
        bar.setPadding(dp(10), dp(7), dp(10), dp(7));
        bar.setBackground(roundRect(NAV_BG, dp(20), BORDER, dp(1)));
        navHome = navigationItem("⌂", "Home", true);
        navEditor = navigationItem("▦", "Editor", false);
        navExport = navigationItem("⇧", "Export", false);
        bar.addView(navHome, new LinearLayout.LayoutParams(0, -1, 1));
        bar.addView(navEditor, new LinearLayout.LayoutParams(0, -1, 1));
        bar.addView(navExport, new LinearLayout.LayoutParams(0, -1, 1));
        navHome.setOnClickListener(v -> navigateTo(homeAnchor, 0));
        navEditor.setOnClickListener(v -> navigateTo(editorAnchor, 1));
        navExport.setOnClickListener(v -> navigateTo(exportAnchor, 2));
        return bar;
    }

    private TextView navigationItem(String symbol, String title, boolean selected) {
        TextView item = label(symbol + "\\n" + title, 12, selected ? ACCENT : MUTED, true);
        item.setGravity(Gravity.CENTER);
        item.setBackground(roundRect(selected ? 0xFF183B29 : NAV_BG, dp(14),
                selected ? 0xFF285B3D : NAV_BG, selected ? dp(1) : 0));
        item.setFocusable(true);
        return item;
    }

    private void navigateTo(View anchor, int selected) {
        if (anchor == null || mainScroll == null) return;
        mainScroll.post(() -> mainScroll.smoothScrollTo(0, Math.max(0, anchor.getTop() - dp(12))));
        styleNavigation(selected);
        anchor.animate().alpha(0.86f).setDuration(90).withEndAction(() ->
                anchor.animate().alpha(1f).setDuration(160).start()).start();
    }

    private void styleNavigation(int selected) {
        TextView[] items = {navHome, navEditor, navExport};
        for (int i = 0; i < items.length; i++) {
            boolean active = i == selected;
            items[i].setTextColor(active ? ACCENT : MUTED);
            items[i].setBackground(roundRect(active ? 0xFF183B29 : NAV_BG, dp(14),
                    active ? 0xFF285B3D : NAV_BG, active ? dp(1) : 0));
        }
    }

    private void animateCards(LinearLayout content) {
        for (int i = 0; i < content.getChildCount(); i++) {
            View child = content.getChildAt(i);
            if (!(child instanceof LinearLayout)) continue;
            child.setAlpha(0f);
            child.setTranslationY(dp(9));
            child.animate().alpha(1f).translationY(0f)
                    .setStartDelay(Math.min(i * 35L, 210L)).setDuration(260L).start();
        }
    }

'''
s = s[:insert_at] + nav_methods + s[insert_at:]

p.write_text(s)
print("Applied emerald theme, bottom navigation and subtle entrance/section animations.")
