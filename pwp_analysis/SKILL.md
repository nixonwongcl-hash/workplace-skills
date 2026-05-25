---
name: PWP Performance Analysis
description: Analyzes PWP Receipt Count performance from Excel data, generating site-specific reports with UTD totals and top/bottom rankings.
---

# PWP Performance Analysis Skill

## 1. Skill Overview
The **PWP Performance Analysis** skill automates the tracking, pivoting, and reporting of Purchase With Purchase (PWP) sales transactions. Taking raw transactional logs containing site, dates, and salesman names, it splits the dataset by outlet, computes daily sales volumes, ranks sales performers, calculates up-to-date (UTD) cumulative totals, and applies professional conditional formatting highlights to identify top and bottom performers on a daily basis.

## 2. Trigger Details
- **Trigger Keywords**: `"analyse pwp"`, `"pwp performance"`, `"pwp rankings"`.
- **Trigger Condition**: Upload of a transaction spreadsheet accompanied by these keywords.

## 3. Data Input Requirements
- **Required Columns**:
  - `SiteCodeName` (The store outlet identification name, e.g. `"KKDG"`)
  - `SalesmanName` (The name of the sales representative)
  - `DocumentDate` (The transaction timestamp or date value)
  - `PWP Receipt Count` (The numerical metric showing PWP transactions)

## 4. Detailed Business & Calculation Logic
1. **Outlet-Based Splitting**: Split the main dataset by unique `SiteCodeName` and generate a dedicated, separate report workbook for each site.
2. **Date Chronological Alignment**: Convert `DocumentDate` to standard date format (`%b %d` for display) and sort columns in ascending chronological order.
3. **Salesman Pivot Mapping**: Generate a pivot table indexing `SalesmanName` against the chronological dates, summing the `PWP Receipt Count`.
4. **Daily Highs Performance**:
   - For each date column, identify the maximum count.
   - If `max_count > 0`, award a "Daily High" count point to the salesman (or multiple salesmen in case of ties) who achieved the maximum sales count.
5. **UTD Total Performance**:
   - Calculate the horizontal sum of all date columns for each salesman to yield their cumulative `UTD Total`.
6. **Dual Rankings Calculation**:
   - **`Rank (Total)`**: Rank salesmen by their `UTD Total` in descending order.
   - **`Rank (Daily #1)`**: Rank salesmen by their accumulated `Daily Highs` points in descending order.
   - *Rank Method*: Standard minimum rank method (`method='min'`).
7. **Grand Total Mapping**: Append a `GRAND TOTAL` row at the bottom summing UTD Totals and individual date columns.

## 5. Output Structure & Formatting Standards
- **Output Directory**: Saved within a generated parent folder named `PWP_Analysis_Results_DDMMYYYY`.
- **File Name Format**: `[SiteName]_[DDMMYYYY].xlsx`
- **Workbook Tab 1 (`Daily Performance`)**:
  - Main sheet containing: `SalesmanName`, `Rank (Total)`, `Rank (Daily #1)`, `UTD Total`, all chronological date columns, and the bottom `GRAND TOTAL` row.
- **Workbook Tab 2 (`UTD Summary`)**:
  - Condensed sheet containing: `SalesmanName`, `Rank (Total)`, `Rank (Daily #1)`, and `UTD Total`.

### Styling & Aesthetics:
- **Header Row Style**: Dark Blue background (`#2C3E50`), White bold text, center-aligned, with border borders.
- **Freeze Panes**: Locked on row 1 and columns A to D (`freeze_panes(1, 4)`) so salesman names and rank metrics remain visible during horizontal date scrolling.
- **Column-Specific Fills**:
  - **Rank Columns**: Light blue background (`#EBF5FB`), centered text.
  - **UTD Total Column**: Light orange background (`#FFF7E6`), bold text.
  - **GRAND TOTAL Row**: Light gray background (`#F2F2F2`), bold text.
- **Daily Performance Conditional Highlighting (Applied to Date Columns only)**:
  - **Green Highlighting (`#C6EFCE` fill, `#006100` text)**: Marks top performer(s) with the maximum sales count for that specific day (if greater than 0).
  - **Red Highlighting (`#FFC7CE` fill, `#9C0006` text)**: Marks bottom performer(s) with the minimum sales count for that specific day (or all sales if max is 0).

## 6. Execution Command
The performance analysis is executed via:
```powershell
python .agent/skills/pwp_analysis/scripts/pwp_analysis.py "path/to/PWP_Raw_Data.xlsx"
```
### Optional Run Flags:
- `--output_root [dir]`: Set custom destination directories for the output folder structure.
