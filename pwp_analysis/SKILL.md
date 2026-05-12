---
name: PWP Performance Analysis
description: Analyzes PWP Receipt Count performance from Excel data, generating site-specific reports with UTD totals and top/bottom rankings.
---

# PWP Performance Analysis Skill

This skill automates the analysis of PWP (Purchase With Purchase) performance data. It takes a raw Excel export containing site, salesman, and date information and produces a set of professionally formatted reports.

## Features
- **Site Splitting**: Automatically generates one Excel file per site.
- **Salesman Tracking**: Pivots data to show daily performance (PWP Receipt Count) for each salesman.
- **UTD Performance**: Adds a 'Up-To-Date' total column and a separate summary tab.
- **Rank Highlighting**: Highlights the top performer in **Green** and the bottom performer in **Red** for every day.
- **Sorted View**: Salesmen are sorted by their overall total performance.

## Usage
To use this skill, the user should provide a PWP Excel file and say "analyse PWP".

### Required Data Columns
The input Excel file must contain these columns:
- `SiteCodeName`
- `SalesmanName`
- `DocumentDate`
- `PWP Receipt Count`

## Implementation
The analysis is performed using a Python script located at `scripts/pwp_analysis.py`.

### Execution Command
```powershell
python c:\Users\USER\.gemini\antigravity\playground\azure-radiation\scripts\pwp_analysis.py "<path_to_excel_file>"
```
