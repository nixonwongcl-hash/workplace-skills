---
name: pbo-gp-analysis
description: Analyzes PBO margin data from Penetration Pivot CSV sheets, prioritizing Brand Outlet (BO) and Own Brand items to identify category winners based on Highest GP%, GP Amount, and Selling Price. Also supports an enhanced mode with composite scoring, MoM trends, and outlet-level breakdowns. Triggered by keywords "pbo gp", "gp penetration", "pbo penetration", "margin optimization".
---

# PBO GP Analysis Skill

## Version
Current version: **v1.0.0** (2026-07-21)

## 1. Skill Overview
The **PBO GP Analysis** skill automates the tracking, prioritization, and margin optimization of products across categories. By loading a master **Penetration Pivot** spreadsheet or CSV log, it filters out duplicates, evaluates product performance, and isolates high-priority items. For every category, it selects three specific category margin "winners" (Highest GP%, Highest absolute GP by unit, and Highest Selling Price per unit), strictly prioritizing **Brand Outlet (BO)** or **Own Brand** brands to drive corporate brand growth.

An optional **enhanced mode** (`--enhanced`) produces a second output file with three sheets: Rankings (same as above), Category Deep Dive (with composite scoring, MoM trends, penetration depth, and absolute GP$), and Outlet-Level Breakdown (per-site drill-down for individual outlet managers).

## 2. Trigger Details
- **Trigger Keywords**: `"pbo gp"`, `"gp penetration"`, `"pbo penetration"`, `"margin optimization"`, `"process gp %"`.
- **Trigger Condition**: Detection of these keywords alongside a raw `Penetration Pivot` tracking CSV or Excel file.

## 3. Data Input Requirements
- **Required Spreadsheets**: Exported raw Penetration Tracker sheet (`PBO Penetration Tracker AM_Penetration Pivot_Pivot table [DDMMYYYY].csv` or equivalent).
- **Required Columns**:
  - `PenetrationTracker` (Main product category, e.g. `"ACTICOL"`, `"ZOLPRA/PANTOMAC"`)
  - `ArticleCode` (Numeric/String unique identifier for items)
  - `ArticleName` (Unique name/description of the item)
  - `BO_Type` (Brand outlet indicator, e.g. `"BO SEMI"`, `"BO FULL"`, `"BO MASS"`, `"Own Brand"`, `"Non-BO"`)
  - `Qty (1S)` (Sales quantity in singles/tablets/capsules, used for direct unit-level normalization)
  - `SalesAmt` (Gross sales amount)
  - `GrossProfit` (Total Gross Profit value)
  - `GP %` (Raw profit margin decimal, e.g. `0.605417` representing `60.54%`, may contain `%` sign)

## 4. Detailed Business & Calculation Logic
1. **Numeric Normalization**: Clean and convert `Qty (1S)`, `SalesAmt`, `GrossProfit`, and `GP %` into standard floating-point numbers. Replace `%` signs in GP% before conversion and divide by 100. Negative quantities are converted to absolute values. Missing values are filled with 0.
2. **Category & Article Grouping**: Group the raw data by `PenetrationTracker` and `ArticleCode` to ensure one row per unique product category item, keeping the first occurrence of `ArticleName` and `BO_Type`.
3. **Weighted GP% Calculation**: Instead of taking the maximum GP% across sites, compute the true article-level margin as `sum(GrossProfit) / sum(SalesAmt)`. This correctly aggregates profit across all sites rather than picking an outlier.
4. **Margin & Unit Metrics**:
   - Products are sold in different pack sizes (e.g. box of 100 vs box of 10). To ensure a fair unit-level comparison across the entire category, quantities are normalized to individual tablets/capsules using the `Qty (1S)` column.
   - `Unit_Selling_Price` = `SalesAmt / Qty (1S)` (where `Qty (1S) > 0`, else `0`).
   - `GP_by_Unit` = `Weighted_GP_Pct * Unit_Selling_Price` (gross profit dollars per capsule/tablet).
5. **BO Priorities (Tiered Sourcing Logic)**:
   - Identify Brand Outlet (BO) items using BO Types list: `['BO SEMI', 'BO FULL', 'BO MASS', 'Own Brand']`.
   - In each category, when ranking products for the three winners, **always select the top BO item first** if any exist. Only fall back to `Non-BO` products if there are no Brand Outlet or Own Brand products available in that category.
6. **Winner Selection (3 per category)**:
   - **Highest GP%**: The product with the maximum weighted GP% value.
   - **Highest GP by SalesAmt**: The product with the maximum computed gross profit dollars per unit (`GP_by_Unit`).
   - **Highest Selling Price**: The product with the maximum `Unit_Selling_Price` per capsule/tablet.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `Penetration_Pivot_Analysis_Results_[DDMMYYYY].xlsx`
- **Output Directory**: Automatically saved directly to the user's `C:\Users\USER\Downloads` folder.
- **Worksheet Name**: `Rankings`
- **Column Order**:
  1. `Main Category` (Left-aligned)
  2. `Rank Type` (Center-aligned)
  3. `Article Code` (Center-aligned)
  4. `Article Description` (Left-aligned)
  5. `BO Type` (Center-aligned)
  6. `Value` (Right-aligned, formatted based on rank type)

### Styling & Aesthetics:
- **Header Row Style**: Sleek Dark Slate background (`#2C3E50`), White bold text, center-aligned, with thin borders.
- **Row Styling**: Alternating background colors grouped by category (alternate color every 3 rows). Alternate row colors use Light Gray (`#F2F4F4`) and White (`#FFFFFF`).
- **Number Formats**:
  * For **Highest GP%** rows: Formatted as percentage (`0.00%`).
  * For **Highest GP by SalesAmt** & **Highest Selling Price** rows: Formatted as currency decimal (`#,##0.00`).
- **Column Dimensions**:
  * `Main Category`: Width 35
  * `Rank Type`: Width 30
  * `Article Code`: Width 15
  * `Article Description`: Width 55
  * `BO Type`: Width 15
  * `Value`: Width 15

## 6. Enhanced Mode Output (--enhanced flag)
When `--enhanced` is specified, a second file is generated with three sheets:

### Sheet 1: Rankings
Same as the standard output above.

### Sheet 2: Category Deep Dive
Per-article table sorted by Composite Score within each category:
- `Main Category` — Product category
- `Article Code` — Unique article identifier
- `Article Description` — Item name
- `BO Type` — Brand classification
- `Weighted GP%` — True margin across all sites (percentage)
- `Unit Selling Price` — Price per unit (RM)
- `Total Qty Sold` — Aggregate volume across all sites
- `Total GP$` — Absolute gross profit contribution (RM)
- `Avg Penetration Depth` — Average market share across sites (% Qty SOB)
- `Avg MoM Trend` — Month-over-month volume change (%)
- `Composite Score` — Weighted multi-dimensional score (0–1 scale)
- `Outlets Covered` — Number of unique sites selling this article

**Composite Score Formula:**
```
score = 0.35 × GP%_norm + 0.25 × Qty_norm + 0.20 × MoM_norm + 0.05 × Penetration_norm + BO_bonus
BO_bonus = 0.15 for BO/Own Brand, 0 for Non-BO
All norms are min-max scaled to [0, 1]
```

### Sheet 3: Outlet-Level Breakdown
Article × Site pivot view for individual outlet managers:
- `Main Category`, `Article Code`, `Article Description`, `BO Type`, `Site`
- `Qty Sold`, `Sales Amt`, `GP$`, `Outlet GP%`, `Penetration %`, `MoM Trend`

## 7. Execution Command
Automate the analysis by executing the production script from the workspace directory:
```powershell
python .agents/skills/pbo_gp_analysis/scripts/pbo_gp_analysis.py -i "C:\Users\USER\Downloads\PBO Penetration Tracker AM_Penetration Pivot_Pivot table 25052026.csv"
```

### Required Flags:
- `-i` / `--input`: Absolute file path to the raw input Penetration Tracker Pivot CSV/Excel file.
- `-o` / `--output` *(Optional)*: Custom target path for the formatted Excel rankings spreadsheet.
- `-e` / `--enhanced` *(Optional)*: Path for the enhanced analysis file with Category Deep Dive and Outlet-Level Breakdown sheets. If omitted, only the standard Rankings output is produced.

Example with both outputs:
```powershell
python .agents/skills/pbo_gp_analysis/scripts/pbo_gp_analysis.py -i "C:\Users\USER\Downloads\PBO Penetration Tracker AM_Penetration Pivot_Pivot table 25052026.csv" -e "C:\Users\USER\Downloads\Penetration_Pivot_Analysis_Enhanced.xlsx"
```
