---
name: Match Local Supplier
description: Maps a reorder list against a local ordering file (e.g., Sabah POISON tab) to append supplier, pricing details, and calculate 30/60 days top-up quantities. Triggered by keywords "match local supplier".
---

# Match Local Supplier Skill

**Trigger:** The user uploads or specifies an Excel Reorder list and a Local Ordering file and uses the keyword "match local supplier".

## Step 1: Clarification
Ensure you know the paths to:
1. **The Reorder List**: (e.g., `All_Outlets_Medicine_Reorder...xlsx`)
2. **The Local Ordering File**: (e.g., `SABAH LOCAL ORDERING .xlsx`)

If the user hasn't provided both, ask for them before proceeding.

## Step 2: Execution Logic
Run the Python script against the provided files.

### Backend Python Script Usage:
```bash
python .agent/skills/match_local_supplier/scripts/match_supplier.py "path/to/reorder_file.xlsx" "path/to/local_ordering_file.xlsx"
```

### Logic Applied:
- The script matches articles from the Reorder file with the `POISON TO ORDER LOCALLY ` tab in the local ordering file.
- It filters the reorder list strictly for the `MEDICINE` category, completely ignoring OTC MEDICINE or any other categories.
- It calculates `Top Up Qty (30 Days)` using `(Daily Demand * 30) - Pipeline Stock` alongside the existing 60-day quantity.
- Unmatched articles will default to `N/A` for Supplier, Same Cost, and Nett Pricing, ensuring no reorder list item is dropped.
- It generates a professional Excel report with two sheets: `Summary By Supplier` (grouped by Store) and `Detailed List`.

## Step 3: Output Formatting
The script automatically applies Rotation-style formatting to the Excel output:
- Black headers with white text.
- Auto-filtered and auto-adjusted column widths.
- All text centered except for `ArticleDesc` which is left-aligned.
- File is saved locally as `Sabah_Local_Ordering_Summary_DDMMYYYY.xlsx` in the same directory as the reorder file.

After the script runs, present a summary markdown table of the total quantities grouped by supplier in the chat interface.
