---
name: Article Check Recall Return
description: Cross-references a Recall/PUR report against SHD stock data to identify outlets holding positive SOH of recalled articles. Excludes zero-stock entries. Triggered by "mass recall", "recall check", "check recall".
---

# Article Check Recall Return Skill

## 1. Skill Overview
The **Article Check Recall Return** skill performs a **Mass Recall Exposure Analysis**. It takes a recall report (from PUR system or manual recall list) as input, extracts the article codes and recall details, then cross-references them against the latest SHD (Stock on Hand) inventory file. The output isolates only stores holding **positive SOH** of recalled articles — zero-stock entries are excluded. This tells you exactly which outlets need action.

## 2. Trigger Details
- **Trigger Keywords**: `"mass recall"`, `"recall check"`, `"check recall"`, `"recall exposure"`, `"pur recall"`.
- **Trigger Condition**: When these keywords are detected, the agent should search for:
  1. A **Recall Report** file in Downloads (e.g., `Recall_Report_*.xlsx`)
  2. The latest **SHD** file in Downloads (e.g., `SHD DDMMYYYY.xlsx`)
  If neither is found, ask the user to provide the paths.

## 3. Data Input Requirements

### Primary Input: Recall Report
- **File Pattern**: `Recall_Report_*.xlsx` or any Excel file containing recall columns
- **Required Columns** (at minimum):
  - `ArticleCode` (Numeric/String — unique article identifier)
  - `ArticleDesc` (String — article description)
  - `Return Reason` (String — e.g., "DIRECTIVE RECALL LEVEL B", "SHORT EXPIRED", "MASS RECALL")
  - `Store Code` or `Outlet Involved` (Numeric — store identifier)
  - `SOH` (Numeric — stock on hand at time of recall)
- **Optional Columns**: `Buyer Remark / Batch`, `Deadline`, `Allocation / Recall No`, `Store Instruction`, `Completion Status`, `Remark`

### Secondary Input: SHD File
- **File Pattern**: `SHD DDMMYYYY.xlsx` (latest date preferred)
- **Required Columns**:
  - `ArticleCode` (Numeric/String)
  - `ArticleDesc` (String)
  - `Store` (String — full store name like "1487 - KKDG")
  - `SOH` (Numeric — current stock on hand)

## 4. Detailed Business & Calculation Logic

1. **Load Recall Report**: Read the recall file, extract unique `ArticleCode` list.
2. **Load SHD File**: Read only necessary columns (`Store`, `ArticleCode`, `ArticleDesc`, `SOH`) to minimize memory usage. Use `dtype={'ArticleCode': str, 'Store': str}` for consistent matching.
3. **Cross-Reference**: Filter SHD rows where `ArticleCode` exists in the recalled codes list.
4. **Exclude Zero Stock**: Keep only rows where `SOH > 0`. These are the outlets that actually need action.
5. **Merge Recall Details**: For each matched SHD row, pull the corresponding recall info (Return Reason, Buyer Remark/Batch, Deadline, Store Instruction, Allocation/Recall No) from the recall report.
6. **Key Standardization**: Normalize `ArticleCode` to integers for matching. Parse store number from `Store` column (e.g., `"1487 - KKDG"` → `1487`).
7. **Sorting**: Sort results alphabetically by `ArticleCode`, then by `Store Code`.

## 5. Output Structure & Formatting Standards

- **File Name Format**: `Mass_Recall_Check_DDMMYYYY.xlsx`
- **Output Directory**: `C:\Users\USER\Downloads\`
- **Worksheet Name**: `Mass Recall Check`
- **Column Order (Exact)**:
  1. `ArticleCode` (Center-aligned)
  2. `ArticleDesc` (Left-aligned)
  3. `Return Reason` (Center-aligned)
  4. `Buyer Remark / Batch` (Center-aligned)
  5. `Outlet Involved` (Center-aligned)
  6. `Store Code` (Center-aligned)
  7. `SOH` (Center-aligned, formatted with thousands separator `#,##0`)
  8. `Allocation / Recall No` (Center-aligned)
  9. `Store Instruction` (Center-aligned)
  10. `Deadline` (Center-aligned)
  11. `Completion Status` (Center-aligned)
  12. `Remark` (Center-aligned)

### Styling & Aesthetics:
- **Font**: Arial (Header size 11, data size 10)
- **Header Row**: Foreground White (`#FFFFFF`), Background Solid Black (`#000000`), bold, center-aligned, wrap text enabled.
- **Data Rows**: Left-aligned for `ArticleDesc` (columns A-B), center-aligned for all others. Wrap text enabled.
- **Borders**: Thin border on all cells.
- **Auto-Filter**: Enabled across all columns (`A1:{last_col}{max_row}`).
- **Widths**: Auto-optimize based on maximum content length + 4 padding, minimum width 12, maximum width 55.

### Summary Output (Console):
After generating the Excel file, print a summary:
```
Saved: C:\Users\USER\Downloads\Mass_Recall_Check_DDMMYYYY.xlsx
Total rows: N, Unique articles: M

ArticleCode | ArticleDesc | Return Reason | SOH | Store | Deadline
...
```

## 6. Execution Command
The processing can be automated by executing the script `process_recall.py`:
```powershell
python .agents/skills/article_check_recall_return/scripts/process_recall.py
```

If no recall file is specified, the script will auto-detect the most recent `Recall_Report_*.xlsx` in `C:\Users\USER\Downloads\` and the most recent `SHD_*.xlsx` file.
