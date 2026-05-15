---
name: Excel Pareto Mapping
description: Maps Pareto sales data (Sales Qty, Sales Amt, CombinedPareto) into an SHD report based on Article Code and Site Code, and generates a summary of unmatched items.
---

# Excel Pareto Mapping

This skill automates the process of mapping sales performance metrics from a Pareto report into a Stock on Hand (SHD) report. It handles large datasets efficiently and identifies items present in sales history but missing from the current inventory report.

## Trigger Keywords
- "map pareto"
- "map sales data to shd"
- "pareto mapping"

## Requirements
- **SHD Report**: An Excel file containing `Store` (e.g., "1487 - KKDG") and `ArticleCode`.
- **Pareto Report**: An Excel file containing `Article Code`, `SiteCode`, and performance metrics.

## Mapping Logic
1. **Site Matching**: Extracts the 4-digit site code from the SHD `Store` column.
2. **Article Matching**: Standardizes Article Codes to strings to ensure lead zeros are handled correctly.
3. **Summary Generation**: Creates a second tab named `Summary` containing all items found in the Pareto report that do not have a corresponding site listing in the SHD report.
4. **Description Recovery**: For unmatched items, it attempts to find the `Article Description` by searching across all sites in the SHD file.

## Usage
When triggered, the agent will:
1. Identify the SHD and Pareto files from the conversation or local downloads.
2. Run the `scripts/map_logic.py` script.
3. Output a consolidated Excel file with `Mapped_SHD` and `Summary` tabs.

## Implementation Details
The skill uses:
- `pandas` for data manipulation.
- `calamine` engine for fast reading of large Excel files.
- `xlsxwriter` for efficient multi-sheet writing.
