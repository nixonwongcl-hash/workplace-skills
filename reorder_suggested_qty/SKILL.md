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
5. **Replenishment Strategies (Raw Calculations)**:
   - **Strat 1 (Top Up 45 - A Only)**: Focuses strictly on keeping core Class A items stocked.
     - If `CombinedPareto == 'A'` and `Logic_SHD < 60 days`, raw reorder = `ceil(Daily Demand * 45)`. Otherwise `0`.
   - **Strat 2 (To 90D - A Only)**: Top-up threshold for high-volume Class A items.
     - If `CombinedPareto == 'A'` and `Logic_SHD < 45 days`, raw reorder = `max(0, ceil((Daily Demand * 90) - Pipeline Stock))`. Otherwise `0`.
   - **Strat 3 (Pareto-Target)**: Standard target-based reorder to bring stock levels to:
     - **Class A**: Target 60 days.
     - **Class B**: Target 45 days.
     - **Class C**: Target 30 days.
     - Formula: `max(0, ceil((Daily Demand * TargetDays) - Pipeline Stock))` where `TargetDays` maps to A=60, B=45, C=30.
   - **Strat 4 (Pareto-Additional)**: Direct injection of supply days for fast rotation if inventory is low.
     - If `Logic_SHD < 60 days`, raw reorder = `ceil(Daily Demand * AdditionalDays)`. Otherwise `0`.
     - `AdditionalDays` maps to A=60, B=45, C=30.
6. **TRP Rounding Logic**:
   - For each strategy, the raw quantity must be rounded to the nearest multiple of TRP:
     - If `TRP <= 1`, final qty = `int(raw_qty)`.
     - If `TRP > 1`, final qty = `int(round(raw_qty / TRP) * TRP)`.
7. **Sorting**: Sort the results in ascending order of Pareto class (A -> B -> C), then by `Strat 3: Pareto-Target` descending.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `[FileName]_Pareto_Analysis.xlsx`
- **Tab 1: `Reorder Details`**: Main worksheet containing the raw dataset with calculated strategy columns appended.
- **Tab 2: `Pareto Analysis`**: Management summary dashboard showing:
  - Rows for Pareto Class `A`, `B`, and `C`.
  - Columns: `Total Articles`, `Strat (Items)` (Count of items with qty > 0), and `Strat (Qty)` (Total sum of quantities) for each of the 4 strategies.

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
