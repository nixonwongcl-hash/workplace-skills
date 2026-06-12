---
name: Reorder Suggested Qty
description: Calculates suggested reorder quantities based on Pareto strategies (A, B, C), using SHD Excel data. Triggered by keywords "calculate reorder", "reorder qty", or "reorder".
---

# Reorder Suggested Qty Skill

## 1. Skill Overview
The **Reorder Suggested Qty** skill automates multi-strategy replenishment forecasting for store inventories. It implements a **Pareto-driven replenishment engine** that dynamically reacts to an item's Pareto classification (Class A, B, or C). It calculates daily demand, computes total pipeline stock, projects supply days, applies distinct reorder strategies, and rounds quantities to fit Target Reorder Pack sizes (TRP) while applying visual alert indicators.

## 2. Trigger Details
- **Trigger Keywords**: `"calculate reorder"`, `"reorder qty"`, `"reorder"`, `"replenish stock"`.
- **Trigger Condition**: When these keywords are detected alongside an uploaded SHD Excel sheet, the skill executes.

## 3. Data Input Requirements
- **Required Columns**:
  - `Pareto` (or `CombinedPareto`, directly present in the source SHD file; there is no need to match or join with a separate Pareto/sales data file)
  - `BO Type` (Filter out rows where `BO Type` is empty/blank)
  - `SOH` (Stock on Hand)
  - `Intransit` (In-transit Stock)
  - `Day 1 to 30`, `Day 31 to 60`, `Day 61-90` (Sales buckets)
  - `TRP` (Target Reorder Pack size, defaults to 1 if missing)
  - `SHD` (Existing stock days, optional)

## 4. Detailed Business & Calculation Logic
1. **Daily Demand Calculation**:
   - `Daily Demand = (Day 1 to 30 + Day 31 to 60 + Day 61-90) / 90`
2. **Pipeline Stock Calculation**:
   - `Pipeline Stock = SOH + Intransit`
3. **Calculated/Logical Stock Days (`Logic_SHD`)**:
   - If `Daily Demand > 0`, `Calc_SHD = Pipeline Stock / Daily Demand`, else `999`.
   - If `SHD` is already present, `Logic_SHD = pd.to_numeric(SHD)`. Otherwise, fall back to `Calc_SHD`.
4. **Target Reorder Pack (TRP) Cleansing**:
   - Normalize `TRP` to an integer, with a minimum value of 1.
5. **Replenishment Strategies (Raw Calculations - Pareto Class A Only)**:
   - **Strat 1 (SHD < 45 - Top Up 45)**:
     - If `Logic_SHD < 45 days`, raw reorder = `ceil(Daily Demand * 45)`. Otherwise `0`.
   - **Strat 2 (SHD < 60 - Top Up 45)**:
     - If `Logic_SHD < 60 days`, raw reorder = `ceil(Daily Demand * 45)`. Otherwise `0`.
6. **TRP Rounding Logic**:
   - For each strategy, the raw quantity must be rounded to the nearest multiple of TRP:
     - If `TRP <= 1`, final qty = `int(raw_qty)`.
     - If `TRP > 1`, final qty = `int(round(raw_qty / TRP) * TRP)`.
7. **Sorting**: Sort the results by `Strat 1: SHD < 45 (Top Up 45)` descending.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `[FileName]_Pareto_Analysis.xlsx`
- **Filtering**: Filters the final output dataset to keep **only** Pareto Class A items.
- **Tab 1: `Reorder Details`**: Main worksheet containing the Pareto Class A dataset with calculated strategy columns appended.
- **Tab 2: `Pareto Analysis`**: Management summary dashboard showing:
  - Rows for Pareto Class `A`.
  - Columns: `Total Articles`, `Strat (Items)` (Count of items with qty > 0), and `Strat (Qty)` (Total sum of quantities) for each of the 2 strategies.

### Styling & Aesthetics:
- **Header Row Style**: Black background, White bold text, center-aligned, with Auto-Filters enabled.
- **Freeze Panes**: Locked on row 1 and columns A & B (`freeze_panes(1, 2)`) to allow scrolling while keeping article identification visible.
- **Alignments**: Center-aligned for all columns except `ArticleDesc`, which is left-aligned. Auto-fitted column widths.
- **Conditional Alert Fills (Applied to Strategy Columns Only)**:
  - **Red Fill (`#FFCDD2`)**: If the article is Class A or B, and current `SOH == 0`. (Critical Out of Stock alert)
  - **Orange Fill (`#FFE0B2`)**: If the article is Class A or B, and current `Logic_SHD < 45 days` (excluding SOH = 0 items). (Low stock warning)
  - **Yellow Fill (`#FFFDE7`)**: If the raw suggested quantity is greater than 0, but TRP rounding reduces it to 0. (TRP bottleneck alert)

## 6. Execution Command
The reorder calculation is performed by executing the python CLI script:
```powershell
python .agent/skills/reorder_suggested_qty/scripts/excel_reorder.py "path/to/SHD_File.xlsx"
```
