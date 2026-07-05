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

## 3. Mandatory Interactive Customization Questions
Before running the report script, the agent **MUST** ask the user these questions to customize the filters and strategies:
1. **Pareto Class Filter**: Which Pareto classes should be included? (Options: A only, A & B, All Classes A/B/C)
2. **RP Type Filter**: Which RP Type should be targeted? (Options: Store SGO only, Store AO only, Manual Order only, No filter)
3. **SHD Threshold**: What is the maximum SHD threshold? (Options: SHD 120 or less, SHD 45 or less, SHD 30 or less, No SHD filter)
4. **Intransit Limit**: What should be the Intransit stock condition? (Options: Intransit = 0 only, No Intransit filter)
5. **Top-Up Strategy**: What is the target Top Up Days calculation strategy? (Options: Top Up 60 Days, Top Up 45 Days, Top Up 30 Days, Default Multi-Strategy)

The agent must use the `ask_question` tool to present these options dynamically.

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
5. **Replenishment Strategies**:
   - **Default Multi-Strategy (Pareto Class A Only)**:
     - **Strat 1 (SHD < 45 - Top Up 45)**:
       - If `Logic_SHD < 45 days`, raw reorder = `ceil(Daily Demand * 45)`. Otherwise `0`.
     - **Strat 2 (SHD < 60 - Top Up 45)**:
       - If `Logic_SHD < 60 days`, raw reorder = `ceil(Daily Demand * 45)`. Otherwise `0`.
   - **Custom Days Override (e.g. `--top_up_days 60`)**:
     - Raw suggested qty = `ceil(Daily Demand * top_up_days)`
6. **TRP Rounding Logic**:
   - For each strategy, the raw quantity must be rounded to the nearest multiple of TRP:
     - If `TRP <= 1`, final qty = `int(raw_qty)`.
     - If `TRP > 1`, final qty = `int(round(raw_qty / TRP) * TRP)`.
7. **Sorting**: Sort the results by the primary strategy column descending.

## 5. Execution Command
The reorder calculation is performed by executing the python CLI script:
```powershell
python .agent/skills/reorder_suggested_qty/scripts/excel_reorder.py "path/to/SHD_File.xlsx" [options]
```

### Supported Options:
- `--pareto <classes>`: Comma-separated list of Pareto classes to include (e.g. `A`, `A,B`).
- `--rp_type <type>`: RP Type substring filter (e.g. `SGO` matches `Store SGO with Forecast`).
- `--max_shd <days>`: Max SHD threshold (e.g. `120`).
- `--intransit_zero`: Flag to filter Intransit == 0.
- `--top_up_days <days>`: Specifies a custom top-up day count override (e.g. `60`).
