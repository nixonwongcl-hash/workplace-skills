---
name: PBO GP Analysis
description: Analyzes PBO margin data from Penetration Pivot CSV sheets, prioritizing Brand Outlet (BO) and Own Brand items to identify category winners based on Highest GP%, GP Amount, and Selling Price. Triggered by keywords "pbo gp", "gp penetration", "pbo penetration", "margin optimization".
---

# PBO GP Analysis Skill

## 1. Skill Overview
The **PBO GP Analysis** skill automates the tracking, prioritization, and margin optimization of products across categories. By loading a master **Penetration Pivot** spreadsheet or CSV log, it filters out duplicates, evaluates product performance, and isolates high-priority items. For every category, it selects three specific category margin "winners" (Highest GP%, Highest absolute GP by SalesAmt, and Highest Selling Price per unit), strictly prioritizing **Brand Outlet (BO)** or **Own Brand** brands to drive corporate brand growth.

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
  - `GP %` (Raw profit margin decimal, e.g. `0.605417` representing `60.54%`)

## 4. Detailed Business & Calculation Logic
1. **Numeric Normalization**: Clean and convert `Qty (1S)`, `SalesAmt`, `GrossProfit`, and `GP %` into standard floating-point numbers, replacing errors or missing values with `0`.
2. **Category & Article Grouping**: Group the raw data by `PenetrationTracker` and `ArticleCode` to ensure one row per unique product category item, keeping the first occurrence of `ArticleName` and `BO_Type`.
3. **Margin & Unit Normalization**:
   - Products are sold in different pack sizes (e.g. box of 100 vs box of 10). To ensure a fair unit-level comparison across the entire category, quantities are normalized to individual tablets/capsules using the `Qty (1S)` column.
   - `Unit_Selling_Price` = `SalesAmt / Qty (1S)` (where `Qty (1S) > 0`, else `0`).
   - `GP_by_SalesAmt` = `GP % * Unit_Selling_Price`.
4. **BO Priorities (Tiered Sourcing Logic)**:
   - Identify Brand Outlet (BO) items using BO Types list: `['BO SEMI', 'BO FULL', 'BO MASS', 'Own Brand']`.
   - In each category, when ranking products for the three winners, **always select the top BO item first** if any exist. Only fall back to `Non-BO` products if there are no Brand Outlet or Own Brand products available in that category.
5. **Winner Selection (3 per category)**:
   - **Highest GP%**: The product with the maximum `GP %` value (expressed as a percentage).
   - **Highest GP by SalesAmt**: The product with the maximum computed gross profit dollars per capsule/tablet (`GP_by_SalesAmt`).
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

## 6. Execution Command
Automate the analysis by executing the production script from the workspace directory:
```powershell
python .agent/skills/pbo_gp_analysis/scripts/pbo_gp_analysis.py -i "C:\Users\USER\Downloads\PBO Penetration Tracker AM_Penetration Pivot_Pivot table 25052026.csv"
```
### Required Flags:
- `-i` / `--input`: Absolute file path to the raw input Penetration Tracker Pivot CSV/Excel file.
- `-o` / `--output` *(Optional)*: Custom target path for the formatted Excel rankings spreadsheet.
