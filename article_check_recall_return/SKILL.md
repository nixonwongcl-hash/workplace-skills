---
name: article-check-recall-return
description: Generates a stock on hand (SOH) check or mass recall report for a specific list of articles using SHD Excel data. Triggered by keyword "check article".
---

# Article Check Recall Return Skill

## Version
Current version: **v1.0.0** (2026-07-21)

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
2. **Filtering**:
   - Filter the dataset strictly for the provided target `ArticleCode` list.
   - Keep only rows where `SOH > 0`.
3. **Column Mapping & Renaming**:
   - Add a `Reason` column mapping the target articles to their respective reasons.
   - Rename the `Store` column to `Outlet Involved`.
4. **Sorting**: Sort the results alphabetically by `ArticleCode`, then by `Outlet Involved`.

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

### Styling & Aesthetics:
- **Font**: Arial (Header size 11, data size 10)
- **Header Row**: Foreground White (`#FFFFFF`), Background Solid Black (`#000000`), bold, center-aligned.
- **Data Rows**: Left-aligned for text descriptions, center-aligned for all other columns.
- **Auto-Filter**: Enabled across columns A to F (`A1:F{max_row}`).
- **Widths**: Auto-optimize column dimensions based on maximum content length with a padding of 4 (`max_len + 4`), minimum width of 12.

## 6. Execution Command
The processing can be automated by executing the script `process_recall.py` which applies these exact rules:
```powershell
python .agent/skills/article_check_recall_return/scripts/process_recall.py
```
