---
name: article-check-recall-return
description: Generates a stock on hand (SOH) check or mass recall report for a specific list of articles using SHD Excel data. Triggered by keyword "check article".
---

# Article Check Recall Return Skill

## Version
Current version: **v1.2.0** (2026-08-08)

## 1. Skill Overview
The **Article Check Recall Return** skill automates the extraction and formatting of stock status data from a master Stock on Hand (SHD) inventory report. It is typically used for auditing specific items, performing quality control sweeps, or executing a **Mass Recall** across stores. The output isolates stores that hold positive stock of the targeted articles and outputs a clean, executive-ready Excel sheet.

## 2. Trigger Details
- **Trigger Keywords**: `"check article"`, `"recall report"`, `"soh check"`, `"check stock on hand"`.
- **Trigger Condition**: When these keywords are detected, the agent should search the conversation or downloads for a master SHD Excel file and proceed with the workflow.

## 3. Data Input Requirements
- **Required Spreadsheet**: Standard master SHD Excel export.
- **Required Columns**:
  - `ArticleCode` (Numeric/String representing unique article numbers)
  - `ArticleDesc` (String describing the article)
  - `Category` (String representing product categories)
  - `Store` (String representing the store identifier, e.g. `"1487 - KKDG"`)
  - `SOH` (Numeric representing current stock on hand)

### Setup Questions to Ask the User:
Before executing, clarify:
1. **Target Article Codes**: What specific article codes should be checked?
   > [!IMPORTANT]
   > If the user provides details (such as description, batch number, reason, stores) but does **not** provide the specific article code(s), you **must** stop and ask the user to clarify/provide the article code(s) first before executing.
2. **Reason**: What is the reason for this check or recall? (e.g. `"Wrong Label"`, `"Short Expiry"`, `"Return to Vendor"`, defaults to `"Article Check"` or `"Mass Recall"` depending on the trigger context).

## 4. Detailed Business & Calculation Logic
1. **Key Standardization**: Normalize `ArticleCode` to integers/strings to prevent matching failures caused by formatting.
2. **Allocation Sheet Reconciliation (mandatory when allocation links are supplied)**:
   - Read spreadsheet metadata first and use the exact visible allocation tab.
   - Read the complete populated allocation table containing `Allocation Table Number`, `Article (SKU)`, and `Store`.
   - Normalize article and store identifiers without losing alphanumeric store codes such as `1Y05`.
   - Reject or flag duplicate store rows that map the same article/outlet to conflicting allocation numbers.
   - Build an exact `(ArticleCode, Store Code) -> Allocation Number` mapping.
   - After SHD filtering, look up every positive-SOH outlet individually. Never assign one article-level allocation number to all outlets unless the allocation table proves it.
   - Mark positive-SOH outlets absent from the allocation table as `NOT LISTED - VERIFY`; never silently omit them.
   - If an article has no allocation link, retain it and mark allocation status `NO ALLOCATION LINK PROVIDED`.
3. **Filtering**:
   - Filter the dataset strictly for the provided target `ArticleCode` list.
   - Keep only rows where `SOH > 0`.
   - Default operational scope is **East Malaysia only**. Filter out West Malaysia outlets before producing detail totals. Preserve alphanumeric East Malaysia store codes.
   - State the applied regional scope explicitly in the workbook summary.
4. **Column Mapping & Renaming**:
   - Add a `Reason` column mapping the target articles to their respective reasons.
   - Rename the `Store` column to `Outlet Involved`.
   - Add `Store Code`, `Allocation Number`, and `Allocation Status` when allocation links are supplied.
   - Add `Store Instruction` for every positive-SOH row using the supplied West/East Malaysia instruction; for East Malaysia reports, use the East Malaysia instruction.
   - Add a blank `Completion Status` column with an Excel dropdown restricted to `NOT AFFECTED` and `DONE KEY-IN`.
   - Add a blank, colour-highlighted `Remark` column as the final column for outlet follow-up notes.
5. **Completeness Reconciliation**:
   - Add a summary covering every requested article, including articles with zero positive SOH.
   - Reconcile requested article count, matched article count, positive-SOH outlet count, total SOH, and allocation exceptions before finalizing.
6. **Sorting**: Sort the results by `ArticleCode`, then by `Store Code` / `Outlet Involved`.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `Recall_Report_DDMMYYYY.xlsx` or `Article_Check_DDMMYYYY.xlsx`
- **Output Directory**: Saved to the local workspace and automatically copied to the user's `C:\Users\USER\Downloads` folder.
- **Worksheet Name**: `Recall Report` or `Article Check`
- **Column Order (Exact)**:
  1. `ArticleCode` (Center-aligned)
  2. `ArticleDesc` (Left-aligned)
  3. `Category` (Center-aligned)
  4. `Reason` (Center-aligned)
  5. `Outlet Involved` (Center-aligned)
  6. `SOH` (Center-aligned, formatted with thousands separator `#,##0`)
  7. `Store Code`
  8. `Allocation Number`
  9. `Allocation Status`
  10. `Store Instruction`
  11. `Completion Status` (dropdown: `NOT AFFECTED`, `DONE KEY-IN`)
  12. `Deadline`
  13. `Remark` (final column, highlighted for manual entry)

### Styling & Aesthetics:
- **Font**: Arial (Header size 11, data size 10)
- **Header Row**: Foreground White (`#FFFFFF`), Background Solid Black (`#000000`), bold, center-aligned.
- **Data Rows**: Left-aligned for text descriptions, center-aligned for all other columns.
- **Auto-Filter**: Enabled across columns A to F (`A1:F{max_row}`).
- **Widths**: Auto-optimize column dimensions based on maximum content length with a padding of 4 (`max_len + 4`), minimum width of 12.
- **Completion Status Colours**: `DONE KEY-IN` uses green fill; `NOT AFFECTED` uses amber fill.
- **Remark Colour**: Blank remark-entry cells use light-yellow fill and the `Remark` column must remain last.

## 6. Execution Command
The processing can be automated by executing the script `process_recall.py` which applies these exact rules:
```powershell
python .agent/skills/article_check_recall_return/scripts/process_recall.py
```
