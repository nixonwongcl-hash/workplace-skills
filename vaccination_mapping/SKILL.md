---
name: vaccination-mapping
description: Maps patient names/IDs from PDF invoices (Klinik Dr. Kheng) to Sabah Vaccination Program tracking Excel sheets. Outputs a report showing the corresponding outlet for each patient.
---

# Vaccination Mapping Skill

## Version
Current version: **v1.0.0** (2026-07-21)

Automates mapping of patients billed in PDF invoices to the master vaccination tracking sheets for the Sabah region.

## Trigger Phrases
- "map vaccination patients"
- "run vaccination mapping"
- "generate patient outlet report"

## What the user will provide (each run)
- One or more **PDF invoice files** (e.g., `BIG PHARMACY (SABAH) SDN BHD -017.pdf`)
- One or more **tracking sources** — either:
  - Local Excel files (e.g., `Sabah Vaccination Program 2026.xlsx`)
  - Google Sheets **Publish-to-web CSV URLs** (File → Share → Publish to web → CSV)
  - Or a **mix** of both

## Usage

### With local Excel files only
```bash
python scripts/map_patients.py \
  --pdfs "Invoice017.pdf" "Invoice015.pdf" \
  --sources "Sabah Vaccination Program 2026.xlsx" \
             "Vaccination Sabah Region - Patient Registration Form.xlsx" \
  --output "Patient_Outlet_Mapping_Report.xlsx"
```

### With Google Sheets URL(s)
```bash
python scripts/map_patients.py \
  --pdfs "Invoice017.pdf" \
  --sources "https://docs.google.com/spreadsheets/d/SHEET_ID/pub?gid=123&output=csv" \
  --output "Patient_Outlet_Mapping_Report.xlsx"
```

### Mix of both
```bash
python scripts/map_patients.py \
  --pdfs "Invoice017.pdf" \
  --sources "Sabah Vaccination Program 2026.xlsx" \
             "https://docs.google.com/spreadsheets/d/SHEET_ID/pub?gid=456&output=csv" \
  --output "Patient_Outlet_Mapping_Report.xlsx"
```

## Output Report Columns
| Column | Description |
|---|---|
| ID | IC/Passport number from PDF |
| Name | Patient name from PDF |
| Source | PDF filename |
| Page | Page number in PDF |
| OutletCode | Matched outlet code (e.g. KKDA, KKCM) |
| OutletName | Matched clinic/staff name |
| MatchStatus | Found / Found (Name Match) / MISSING IN EXCEL |
| Is_Duplicated_In_PDF | True if same ID appears more than once in PDFs |

## Auto-detection: Excel Config
The script auto-detects the layout based on filename keywords:
- `Sabah Vaccination Program` → reads `Master Tracking` sheet
- `Patient Registration Form` → reads `Patient List` sheet

## GitHub
This skill is version-controlled. Every update must be committed and pushed.

## Dependencies
```
pdfplumber
pandas
openpyxl
requests
```
Install: `pip install pdfplumber pandas openpyxl requests`
