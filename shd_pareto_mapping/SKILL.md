---
name: SHD Pareto Mapping
description: Maps Pareto sales data (Sales Qty, Sales Amt, CombinedPareto) into an SHD report based on Article Code and Site Code, and generates a summary of unmatched items.
---

# SHD Pareto Mapping Skill

## 1. Skill Overview
The **SHD Pareto Mapping** skill automates the integration of sales performance metrics (e.g. quantities, amounts, and Pareto class classifications) from a sales performance report into a master Stock on Hand (SHD) inventory report. It matches entries by a composite key of Article Code and Store/Site Code. Additionally, it audits the dataset to find items present in the sales history that are missing from the current store inventory and outputs a detailed summary.

## 2. Trigger Details
- **Trigger Keywords**: `"map pareto"`, `"map sales data to shd"`, `"pareto mapping"`, `"map sales metrics"`.
- **Trigger Condition**: When these keywords are matched alongside two uploaded files (the SHD inventory report and the Pareto sales report), this skill should be executed.

## 3. Data Input Requirements
- **SHD Report File**: Excel sheet containing:
  - `Store` (e.g. `"1487 - KKDG"`)
  - `ArticleCode` (Unique identifier)
  - `ArticleDesc` (Description, used to recover missing descriptions)
- **Pareto Report File**: Excel sheet containing:
  - `Article Code` (Unique identifier)
  - `SiteCode` (4-digit site code, e.g. `"1487"`)
  - `Sales Qty (Past 3 Months)`
  - `Sales Amt (Past 3 Months)`
  - `CombinedPareto` (Pareto category classification, e.g. `A`, `B`, `C`)
  - `NewListing` (Optional, flags newly listed items)

## 4. Detailed Business & Calculation Logic
1. **Key Standardization**: Normalize Article Codes and Site Codes as stripped strings to avoid failures from leading zeros or floating-point conversions:
   - `ArticleCode_key` = `str(ArticleCode).split('.')[0].strip()`
   - `SiteCode_key` = `str(SiteCode).split('.')[0].strip()`
2. **Site Code Extraction (SHD)**: Extract the 4-digit code from the SHD `Store` column by splitting on the hyphen delimiter:
   - `df_shd['SiteCode_key'] = df_shd['Store'].str.split(' - ').str[0].str.strip()`
3. **Left Join Mapping**: Perform a left join of the standardized Pareto subset into the standardized SHD dataset using the composite key `['ArticleCode_key', 'SiteCode_key']`.
4. **Unmatched Items Identification**: Locate records in the Pareto report that are entirely absent in the SHD report (using `indicator=True` in a left merge and filtering on `left_only`).
5. **Description Recovery Lookup**: For unmatched articles, map their descriptions (`Article Description`) by searching for the corresponding `ArticleCode_key` across all other stores listed in the master SHD file. If not found in any store, default the description to `"Not found in SHD"`.

## 5. Output Structure & Formatting Standards
- **File Name Format**: `[FileName]_Mapped.xlsx` or a custom output path.
- **Workbook Tab 1 (`Mapped_SHD`)**: Contains the complete master SHD data with the mapped Pareto columns: `Sales Qty (Past 3 Months)`, `Sales Amt (Past 3 Months)`, and `CombinedPareto` appended.
- **Workbook Tab 2 (`Summary`)**: Contains unmatched items with columns:
  - `Article Code`
  - `Article Description` (recovered via lookup)
  - `NewListing` (if present)
  - `SiteCode`

### Styling & Aesthetics:
- **Header Row Style**: Solid Black background, White bold text, center-aligned.
- **Data Alignments**: Center-aligned for all columns except text descriptions (`ArticleDesc`, `Article Description`), which must be left-aligned.
- **Auto-Filter**: Enabled on all headers for sheets `Mapped_SHD` and `Summary`.
- **Column Dimensions**: Automatically auto-fitted based on maximum text length with padding.

## 6. Execution Command
The mapping can be executed programmatically via the backend script `map_logic.py`:
```powershell
python .agent/skills/shd_pareto_mapping/scripts/map_logic.py --shd "path/to/SHD.xlsx" --pareto "path/to/Pareto.xlsx" --output "path/to/Output.xlsx"
```
