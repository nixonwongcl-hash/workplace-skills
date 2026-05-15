---
name: Excel Reorder Calculation
description: Calculates suggested reorder quantities based on Pareto strategies (A, B, C), using SHD Excel data. Triggered by keywords "calculate reorder", "reorder qty", or "reorder".
---

# Excel Reorder Calculation (Pareto Edition)

**Trigger:** The user uploads an Excel SHD inventory file and uses keywords like "calculate reorder", "reorder qty", or "reorder". 

## Step 1: Execution Logic
This skill implements a **Pareto-driven replenishment strategy** based on the article's principles. It automatically detects the `CombinedPareto` column (mapping blanks to Class C) and calculates four distinct strategies.

### Backend Python Script Usage:
```bash
python .agent/skills/excel_reorder/scripts/excel_reorder.py "path/to/input_file.xlsx"
```

### Pareto Strategies Applied:
1.  **Strat 1 (A-Only Top-Up 45):** For Class A items, if SHD < 60, suggest an additional 45 days of supply.
2.  **Strat 2 (A-Only To-90 Days):** For Class A items, if SHD < 45, top up to a total of 90 days of supply.
3.  **Strat 3 (Pareto-Target):** Standard target-based reorder:
    *   **Class A:** Target 60 days.
    *   **Class B:** Target 45 days.
    *   **Class C:** Target 30 days.
4.  **Strat 4 (Pareto-Additional):** Pure addition of supply days regardless of current stock:
    *   **Class A:** +60 days.
    *   **Class B:** +45 days.
    *   **Class C:** +30 days.

## Step 2: Output Formatting
The script generates a single Excel file: `[FileName]_Pareto_Analysis.xlsx`.

### Tab 1: `Reorder Details`
- Contains all raw data with appended strategy columns.
- Sorted by Pareto Class (A -> B -> C) then by priority.
- Column headers are **black with white text**.
- Freeze panes on headers and article info for easy navigation.

### Tab 2: `Pareto Analysis`
- A high-level summary for management.
- Shows item counts and total quantities for each of the 4 strategies, broken down by Pareto Class.
- Used to analyze the potential stock investment impact of each strategy.
