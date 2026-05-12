---
name: Excel Reorder Calculation
description: Calculates suggested reorder quantities based on user-defined target days, using SHD Excel data. Triggered by keywords "calculate reorder", "reorder qty", or "reorder".
---

# Excel Reorder Calculation Skill

**Trigger:** The user uploads an Excel SHD inventory file and uses keywords like "calculate reorder", "reorder qty", or "reorder".

## Step 1: Mandatory Clarification
**CRITICAL:** Before processing any data or running the script, you **MUST** ask the user the following question:
1. **Target Days:** What are the target days of supply you want to calculate the reorder quantity for? (e.g., "30 and 60 days", "90 days only"). Please specify the exact numbers.

*Wait for the user's response to this question before proceeding to Step 2.*

## Step 2: Execution Logic
Once the user provides the target days, execute the Python script `scripts/excel_reorder.py` against the uploaded file.

### Backend Python Script Usage:
```bash
python .agent/skills/excel_reorder/scripts/excel_reorder.py "path/to/input_file.xlsx" --days 30 60
```
*(Pass the user-specified days as space-separated values to the `--days` argument. For example, if they said 30 and 45, pass `--days 30 45`)*

### Logic Applied:
- The script uses the high-performance `calamine` engine to read the Excel file.
- It calculates `Daily Demand` using: `(Day 1 to 30 + Day 31 to 60 + Day 61-90) / 90`.
- It drops rows where `BO Type` is completely blank.
- It calculates `Pipeline Stock` as `SOH + OpenPO + OpenSTO + Intransit`.
- For each requested Target Day, it adds a column: `Suggested Qty (P{day}) = (Daily Demand * {day}) - Pipeline Stock` (minimum 0).

## Step 3: Output Formatting
The script will generate exactly TWO Excel output files in the same directory as the input file, following these styling rules:
- All columns text are conditionally aligned to the **center**, EXCEPT the `ArticleDesc` column which is **aligned to the left**.
- Apply Excel data filters across all headers.
- Format the header row background to **black** and the font color to **white**.
- Auto-optimize all column widths to fit the content cleanly.

### File 1: `Reorder DDMMYYYY.xlsx`
(assuming the input file had "SHD" in the name, it is replaced with "Reorder").
This contains the full detailed data with the newly appended `Suggested Qty` columns.

### File 2: `Reorder_History_Summary DDMMYYYY.xlsx`
This contains a quick summary of:
- Total Lines Processed
- Items needing an order for each target day
- Total Quantity to order for each target day
