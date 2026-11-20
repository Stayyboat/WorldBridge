from pathlib import Path
p = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
s = p.read_text()
s = s.replace('''        root.addView(buildBottomNavigation(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(66)));''', '''        LinearLayout.LayoutParams navParams = new LinearLayout.LayoutParams(
                dp(292), dp(62));
        navParams.gravity = Gravity.CENTER_HORIZONTAL;
        navParams.topMargin = dp(4);
        navParams.bottomMargin = dp(8);
        root.addView(buildBottomNavigation(), navParams);''')
start = s.index('    private View buildBottomNavigation() {')
end = s.index('    private void animateCards(', start)
new = r'''    private View buildBottomNavigation() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER);
        bar.setPadding(dp(6), dp(6), dp(6), dp(6));
        bar.setElevation(dp(12));
        bar.setBackground(roundRect(0xE610251C, dp(31), 0xFF315A42, dp(1)));
        navHome = navigationItem("⌂", "Home", true);
        navEditor = navigationItem("▦", "Editor", false);
        navExport = navigationItem("↥", "Export", false);
        bar.addView(navHome, new LinearLayout.LayoutParams(0, -1, 1));
        bar.addView(navEditor, new LinearLayout.LayoutParams(0, -1, 1));
        bar.addView(navExport, new LinearLayout.LayoutParams(0, -1, 1));
        navHome.setOnClickListener(v -> navigateTo(homeAnchor, 0));
        navEditor.setOnClickListener(v -> navigateTo(editorAnchor, 1));
        navExport.setOnClickListener(v -> navigateTo(exportAnchor, 2));
        return bar;
    }

    private TextView navigationItem(String symbol, String title, boolean selected) {
        TextView item = label(symbol + "\n" + title, 11, selected ? ACCENT : MUTED, true);
        item.setGravity(Gravity.CENTER);
        item.setLineSpacing(0, 0.92f);
        item.setBackground(roundRect(selected ? 0xFF204A32 : 0x0010251C, dp(24),
                selected ? 0xFF397B52 : 0x0010251C, selected ? dp(1) : 0));
        item.setFocusable(true);
        item.setClickable(true);
        return item;
    }

    private void navigateTo(View anchor, int selected) {
        if (anchor == null || mainScroll == null) return;
        mainScroll.post(() -> mainScroll.smoothScrollTo(0, Math.max(0, anchor.getTop() - dp(12))));
        styleNavigation(selected);
        anchor.animate().alpha(0.92f).setDuration(100).withEndAction(() ->
                anchor.animate().alpha(1f).setDuration(180).start()).start();
    }

    private void styleNavigation(int selected) {
        TextView[] items = {navHome, navEditor, navExport};
        for (int i = 0; i < items.length; i++) {
            boolean active = i == selected;
            items[i].setTextColor(active ? ACCENT : MUTED);
            items[i].setBackground(roundRect(active ? 0xFF204A32 : 0x0010251C, dp(24),
                    active ? 0xFF397B52 : 0x0010251C, active ? dp(1) : 0));
            items[i].animate().scaleX(active ? 1.035f : 0.97f)
                    .scaleY(active ? 1.035f : 0.97f).setDuration(210)
                    .setInterpolator(new android.view.animation.OvershootInterpolator(0.65f)).start();
        }
    }

'''
s = s[:start] + new + s[end:]
# Give the page a little extra bottom breathing room for the floating capsule.
s = s.replace('content.setPadding(dp(18), dp(22), dp(18), dp(28));',
              'content.setPadding(dp(18), dp(22), dp(18), dp(38));')
p.write_text(s)
print("Refined the bottom navigation into a floating, spring-animated capsule inspired by the supplied Streak reference.")
