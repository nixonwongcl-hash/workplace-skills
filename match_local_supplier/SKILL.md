---
name: match-local-supplier
description: Maps a reorder list against a local ordering file (e.g., Sabah POISON tab) to append supplier, pricing details, and calculate 30/60 days top-up quantities. Triggered by keywords "match local supplier".
---

# Match Local Supplier Skill

## Version
Current version: **v1.0.0** (2026-07-21)

## 1. Skill Overview
The **Match Local Supplier** skill integrates regional vendor-sourcing details into calculated reorder proposals. It matches articles from a calculated reorder list against a master Local Ordering database (specifically target sheets like `POISON TO ORDER LOCALLY `). The skill filters target items strictly to the human medicine segment, fetches vendor names, nett costs, and pricing structures, calculates top-ups for alternate duration coverage, and aggregates results.

## 2. Trigger Details
- **Trigger Keywords**: `"match local supplier"`, `"sabah supplier matching"`, `"map local supplier"`.
- **Trigger Condition**: When these keywords are triggered, the agent must check for two files: the computed reorder spreadsheet and the master local ordering sheet.

## 3. Data Input Requirements
- **Reorder List File**: Excel sheet containing calculated columns:
  - `Category` (Used to isolate human medicines)
  - `ArticleCode`
  - `Daily Demand`
  - `Pipeline Stock`
  - `Top Up Qty (60 Days)` (Precalculated reorder amount)
- **Local Ordering File**: Excel sheet containing a tab named `POISON TO ORDER LOCALLY ` with columns:
  - `Article Code` (Vendor mapping key)
  - `SUPPLIER` (Vendor name)
  - `SAME COST (Y/N)` (Pricing status indicator)
  - `Nett  cost (YES/NO)` (Nett cost status indicator)

## 4. Detailed Business & Calculation Logic
1. **Strict Medicine Filtering**:
   - Filter the input reorder list strictly for `Category == 'MEDICINE'` (case-insensitive).
   - Ignore `OTC MEDICINE` or any other non-prescription categories.
2. **Key Standardization**:
   - Strip decimals and trailing whitespace from article codes:
     - `ArticleCode = str(ArticleCode).split('.')[0].strip()`
3. **Data Merging**:
   - Perform a left join of the reorder list with the local ordering mapping database.
   - For articles with no matched local supplier, default mapping columns (`Supplier`, `Same Cost`, `Nett Pricing`) to `"N/A"` to ensure no line items are dropped.
4. **Alternative Coverage Calculations**:
   - Compute `Top Up Qty (30 Days)` using the daily demand rate:
     - Formula: `Top Up Qty (30 Days) = ceil((Daily Demand * 30) - Pipeline Stock)`
     - Clip the quantity to a minimum value of `0`.
5. **Sorting & Aggregation**:
   - Sort detailed rows alphabetically by Supplier, then by Store, and finally by ArticleCode.
   - Sort the summary sheet by Store, then Supplier, then by `Top Up Qty (60 Days)` descending.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `Sabah_Local_Ordering_Summary_DDMMYYYY.xlsx` (saved in the same directory as the input reorder list).
- **Workbook Tab 1 (`Summary By Supplier`)**:
  - Aggregated view grouped by `Store`, `Supplier`, `ArticleCode`, `ArticleDesc`, `Same Cost`, and `Nett Pricing`.
  - Sums both `Top Up Qty (30 Days)` and `Top Up Qty (60 Days)`.
- **Workbook Tab 2 (`Detailed List`)**:
  - Full item-level details containing: `Store`, `ArticleCode`, `ArticleDesc`, `Brand`, `Category`, `SOS`, `SOH`, `Top Up Qty (30 Days)`, `Top Up Qty (60 Days)`, `Supplier`, `Same Cost`, `Nett Pricing`.

### Styling & Aesthetics:
- **Header Row Style**: Black background, White bold text, center-aligned, with Auto-Filters.
- **Data Alignments**: Center-aligned for all columns except the `ArticleDesc` text column (left-aligned).
- **Auto-Width Scaling**: Auto-optimize columns to match maximum text size with a safety limit of 50.
- **IM Chat Integration**: Print a clean Markdown table summarizing the total `Top Up Qty` (30 days and 60 days) grouped by Supplier directly in the chat interface.

## 6. Execution Command
The matching is automated via the python script:
```powershell
python .agent/skills/match_local_supplier/scripts/match_supplier.py "path/to/reorder_file.xlsx" "path/to/local_ordering_file.xlsx"
```
