from pathlib import Path

path = Path("app/src/main/java/com/worldbridge/app/MainActivity.java")
source = path.read_text()


def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    source = source.replace(old, new, 1)


# Rounded dialog surfaces with the same charcoal, border and lavender palette as the app.
import_line = "import android.graphics.drawable.GradientDrawable;\n"
replace_once(
    import_line,
    import_line + "import android.graphics.drawable.InsetDrawable;\n",
    "InsetDrawable import",
)

review_dialog = """        new AlertDialog.Builder(this)
                .setTitle("Review chunk removal")
                .setMessage(details)
                .setNegativeButton("Go back", null)
                .setPositiveButton("Delete selected chunks", (dialog, which) -> pruneSelected(dimensionIndex, removeSavedData))
                .show();"""
replace_once(
    review_dialog,
    """        showThemedConfirmation(new AlertDialog.Builder(this)
                .setTitle("Review chunk removal")
                .setMessage(details)
                .setNegativeButton("Go back", null)
                .setPositiveButton("Delete selected chunks", (dialog, which) -> pruneSelected(dimensionIndex, removeSavedData))
                .create(), "Review chunk removal");""",
    "Review Selected Area dialog",
)

delete_dialog = """        new AlertDialog.Builder(this)
                .setTitle("Delete imported world?")
                .setMessage("This removes the imported world and its protected and working copies from WorldBridge. It does not delete the original .mcworld file you selected or any world installed in Minecraft.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Delete", (dialog, which) -> deleteImportedWorld())
                .show();"""
replace_once(
    delete_dialog,
    """        showThemedConfirmation(new AlertDialog.Builder(this)
                .setTitle("Delete imported world?")
                .setMessage("This removes the imported world and its protected and working copies from WorldBridge. It does not delete the original .mcworld file you selected or any world installed in Minecraft.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Delete", (dialog, which) -> deleteImportedWorld())
                .create(), "Delete imported world?");""",
    "Delete World dialog",
)

restore_dialog = """        new AlertDialog.Builder(this)
                .setTitle("Restore original copy?")
                .setMessage("The edited copy will be replaced with the protected original copy. The imported file remains unchanged.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Restore", (dialog, which) -> resetWorkingCopy())
                .show();"""
replace_once(
    restore_dialog,
    """        showThemedConfirmation(new AlertDialog.Builder(this)
                .setTitle("Restore original copy?")
                .setMessage("The edited copy will be replaced with the protected original copy. The imported file remains unchanged.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Restore", (dialog, which) -> resetWorkingCopy())
                .create(), "Restore original copy?");""",
    "Restore confirmation dialog",
)

anchor = "    private void reviewAndPrune() {\n"
if source.count(anchor) != 1:
    raise SystemExit("Could not find dialog helper insertion point.")

helper = """    private AlertDialog showThemedConfirmation(AlertDialog dialog, String titleText) {
        dialog.setOnShowListener(ignored -> {
            android.view.Window window = dialog.getWindow();
            if (window != null) {
                window.setBackgroundDrawable(new InsetDrawable(
                        roundRect(PANEL, dp(20), BORDER, dp(1)), dp(10)));
                android.view.WindowManager.LayoutParams attributes = window.getAttributes();
                attributes.dimAmount = 0.62f;
                window.setAttributes(attributes);
                window.addFlags(android.view.WindowManager.LayoutParams.FLAG_DIM_BEHIND);
            }

            TextView title = findDialogTitle(
                    window != null ? window.getDecorView() : dialog.getWindow().getDecorView(),
                    titleText);
            if (title != null) {
                title.setTextColor(TEXT);
                title.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
                title.setTextSize(18);
                title.setIncludeFontPadding(false);
            }

            TextView message = dialog.findViewById(android.R.id.message);
            if (message != null) {
                message.setTextColor(MUTED);
                message.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
                message.setTextSize(14);
                message.setLineSpacing(dp(3), 1.0f);
            }

            styleDialogButton(dialog.getButton(AlertDialog.BUTTON_NEGATIVE), false);
            styleDialogButton(dialog.getButton(AlertDialog.BUTTON_POSITIVE), true);
            spaceDialogButtons(dialog);
        });
        dialog.show();
        return dialog;
    }

    private TextView findDialogTitle(View root, CharSequence expectedTitle) {
        if (root instanceof TextView) {
            TextView candidate = (TextView) root;
            if (expectedTitle != null && expectedTitle.toString().contentEquals(candidate.getText())) {
                return candidate;
            }
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) {
                TextView found = findDialogTitle(group.getChildAt(i), expectedTitle);
                if (found != null) return found;
            }
        }
        return null;
    }

    private void spaceDialogButtons(AlertDialog dialog) {
        Button negative = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);
        Button positive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
        if (negative == null || positive == null) return;

        ViewGroup buttonBar = (ViewGroup) negative.getParent();
        if (buttonBar == null || positive.getParent() != buttonBar) return;

        if (buttonBar instanceof LinearLayout) {
            ((LinearLayout) buttonBar).setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        }
        buttonBar.setPadding(dp(16), buttonBar.getPaddingTop(), dp(16), buttonBar.getPaddingBottom());

        ViewGroup.MarginLayoutParams negativeParams =
                (ViewGroup.MarginLayoutParams) negative.getLayoutParams();
        negativeParams.width = ViewGroup.LayoutParams.WRAP_CONTENT;
        negativeParams.setMargins(dp(5), negativeParams.topMargin, dp(5), negativeParams.bottomMargin);
        negative.setLayoutParams(negativeParams);

        ViewGroup.MarginLayoutParams positiveParams =
                (ViewGroup.MarginLayoutParams) positive.getLayoutParams();
        positiveParams.width = ViewGroup.LayoutParams.WRAP_CONTENT;
        positiveParams.setMargins(dp(5), positiveParams.topMargin, dp(5), positiveParams.bottomMargin);
        positive.setLayoutParams(positiveParams);

        negative.setMinWidth(dp(76));
        positive.setMinWidth(dp(76));
    }

    private void styleDialogButton(Button button, boolean primary) {
        if (button == null) return;
        button.setAllCaps(false);
        button.setTextSize(13);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        button.setTextColor(primary ? BG : TEXT);
        button.setMinHeight(0);
        button.setMinimumHeight(dp(40));
        button.setPadding(dp(14), 0, dp(14), 0);
        button.setBackground(roundRect(
                primary ? ACCENT : PANEL_SOFT,
                dp(11),
                primary ? ACCENT : BORDER,
                dp(1)));
    }

"""
source = source.replace(anchor, helper + anchor, 1)

path.write_text(source)
print("Applied WorldBridge charcoal/lavender dialog styling to review, delete-world and restore confirmations.")
