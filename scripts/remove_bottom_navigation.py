from pathlib import Path

path = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = path.read_text()


def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    source = source.replace(old, new, 1)


# Remove state used only by the Home / Editor / Export navigation capsule.
replace_once(
    """    private ScrollView mainScroll;
    private View homeAnchor;
    private View editorAnchor;
    private View exportAnchor;
    private TextView navHome;
    private TextView navEditor;
    private TextView navExport;
""",
    "",
    "bottom-navigation fields",
)

# The main screen is now the ScrollView itself; no vertical root is needed.
replace_once(
    """        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

""",
    "",
    "navigation root container",
)
replace_once(
    """        mainScroll = scroll;
""",
    "",
    "main scroll reference",
)

# Remove section anchors that were only used by the navigation buttons.
replace_once("        homeAnchor = importCard;\n", "", "home navigation anchor")
replace_once("        editorAnchor = selectionCard;\n", "", "editor navigation anchor")
replace_once("        exportAnchor = exportCard;\n", "", "export navigation anchor")

# Restore normal page padding after removing the floating capsule.
replace_once(
    "        content.setPadding(dp(18), dp(22), dp(18), dp(38));",
    "        content.setPadding(dp(18), dp(22), dp(18), dp(26));",
    "bottom content spacing",
)

# Give the ScrollView the full screen and preserve the existing card entrance animation.
replace_once(
    """        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        LinearLayout.LayoutParams navParams = new LinearLayout.LayoutParams(
                dp(292), dp(62));
        navParams.gravity = Gravity.CENTER_HORIZONTAL;
        navParams.topMargin = dp(4);
        navParams.bottomMargin = dp(8);
        root.addView(buildBottomNavigation(), navParams);
        setContentView(root);
        animateCards(content);
""",
    """        setContentView(scroll);
        animateCards(content);
""",
    "bottom navigation layout",
)

# Delete the navigation capsule and its click/scroll handlers altogether.
start_token = "    private View buildBottomNavigation() {"
end_token = "    private void animateCards(LinearLayout content) {"
if source.count(start_token) != 1 or source.count(end_token) != 1:
    raise SystemExit("Could not locate the bottom navigation method block exactly once")
start = source.index(start_token)
end = source.index(end_token, start)
if end <= start:
    raise SystemExit("Invalid bottom navigation method boundaries")
source = source[:start] + source[end:]

path.write_text(source)
print("Removed the Home / Editor / Export bottom navigation capsule and its handlers.")
