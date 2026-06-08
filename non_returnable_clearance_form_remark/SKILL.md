---
name: Non Returnable Clearance Form Remark
description: "Analyzes an Excel-based clearance list against SHD report to determine clearance actions and stock rotation suggestions for nearing expiration items."
---

# Non Returnable Clearance Form Remark Skill

## 1. Skill Overview
The **Non Returnable Clearance Form Remark** skill processes manual clearance spreadsheets of retail inventory that is near expiry or non-returnable. It cross-references items against a master Stock on Hand (SHD) report and a regional 9999 listing database to determine store-level clearance instructions and identify optimal internal stock transfer (rotation) opportunities. It generates highly specific remarks based on poison classes, expiry dates, and warehouse locations.

## 2. Trigger Details
- **Trigger Keywords**: `"non returnable clearance"`, `"clearance rotation"`, `"expiry clearance matching"`.
- **Trigger Condition**: When these keywords are detected alongside an uploaded clearance spreadsheet and a master SHD file.

## 3. Data Input Requirements
1. **Clearance Excel File**: A manual listing. The sheet tab name should match the 4-digit or text store identifier of the Sender (e.g. `KKDG`). It must contain:
   - `Article No` (Numeric or string article code)
   - `Expiry` (MM/YY, MM/YYYY, DD/MM/YY, or DD/MM/YYYY dates)
   - `Qty` (Sender's stock on hand available for transfer)
2. **SHD Report File**: Standard master SHD Excel file containing demand rates and receiver inventory parameters (`SOH`, `SHD`, `Day 1 to 30`, `Day 31 to 60`, `Day 61-90`, `Store`).
3. **9999 Poison List File**: Located at `C:\Users\USER\Downloads\SABAH REGION POISON 9999.xlsx` containing:
   - `ARTICLE NO` (Checked to identify specialized regional guidelines)

## 4. Detailed Business & Calculation Logic

### Date Parsing Rules:
- Dates can be formatted in multiple styles (e.g., `DD/MM/YYYY`, `DD/MM/YY`, `MM/YYYY`, `MM/YY`, `YYYY-MM-DD`, with dot or hyphen separators).
- Standardize years (if 2-digit, map to `20xx`).
- The reference date is anchored to **2026-05-01**.
- Expiry month difference is calculated as: `MonthsDiff = (ExpiryYear - 2026) * 12 + ExpiryMonth - 5`.

### Expiry Remarks Decision Matrix:

#### A. Expiry <= 3 Months (Clearance Mode)
- **If MonthsDiff < 1 (Expiring this month)**:
  - `PoisonClass` contains `"NON-POISON"` / `"NON POISON"`: `Continue sell under clearance price. GWP to customer.`
  - `PoisonClass` contains `"GROUP B"`: `Continue sell under clearance price. Submit monthly write off with proof.`
  - `PoisonClass` contains `"GROUP C"`: `DISPENSIBLE! Continue sell under clearance price, no write off allowed.`
  - Other classes: `Continue sell under clearance price. GWP to customer.`
- **If 1 <= MonthsDiff < 2 (Expiring in 1-2 months)**:
  - `"GROUP B"`: `Continue sell under clearance price. Submit monthly write off with proof.`
  - `"GROUP C"`: `DISPENSIBLE! Continue sell under clearance price, no write off allowed.`
  - Other classes: `Continue sell under clearance price. GWP to customer when nearing 1 month.`
- **If 2 <= MonthsDiff <= 3 (Expiring in 2-3 months)**:
  - `"GROUP B"`: `Continue sell under clearance price. Submit monthly write off with proof.`
  - `"GROUP C"`: `DISPENSIBLE! Continue sell under clearance price, no write off allowed.`
  - Other classes: `Continue sell under clearance price.`
- *Receiver Suffix*: If an optimal receiver is found, append `(Suggested receiver: <Receiver>, Qty: <TransferQty>, Contact for consent)` to the clearance remark.

#### B. Expiry > 3 Months (Rotation Mode)
- If an optimal receiver is found: Remark = `Rotate to <Receiver>, Qty: <TransferQty>`.
- If no receiver is found: Remark = `Continue sell under clearance price.`.

### Special Remark Overrides:
- **Sabah 9999 List Override**: If the article is a Poison Class (Group B/C) and is present in the `SABAH REGION POISON 9999.xlsx` listing, the remark **MUST** be prefixed with `[Refer to Sabah Region 9999 List]`.
- **Group C Dispenible Rule**: If the item is Group C and has no suggested receiver, the remark **MUST** start or contain `DISPENSIBLE!`.

### Cluster Routing & Sourcing Logic:
- **Cluster 1 Outlets**: (`KKDG`, `KKIN`, `KKCM`, `KKGM`, `KKJP`, `KKDA`, `SAKN`, `SABF`, `SATR`, `KKLD`)
  - Can only rotate to stores within Cluster 1.
- **Cluster 2 Outlets**: (`SALD`, `SATW`)
  - Can rotate within Cluster 2 first. If no suitable receiver exists in Cluster 2, they are allowed to offer stock to Cluster 1 stores.
- **Receiver Filtering**: Only stores with `SHD_Num <= 30 Days` and `Daily Demand > 0` are eligible to receive.
- **Receiver Top-Up Target**: Receivers are topped up to `120 Days` of supply:
  - `Target Qty = ceil((Daily Demand * 120) - SOH_Num)`
  - Suggested transfer quantity is `min(Target Qty, Sender Available Qty)`.
- **Receiver Selection Priority**: Sort potential receivers by `Daily Demand` descending, then by `SHD_Num` ascending (picking the store with the highest demand and lowest stock days).

## 5. Output Structure & Formatting Standards
- **File Name Format**: `Non_Returnable_Clearance_Combined_DDMMYYYY_HHMM.xlsx`
- **Output Directory**: Saved to `C:\Users\USER\Downloads`.
- **Workbook Structure**: Dynamically creates a tab sheet for each sender store processing run (sheet tab names matching the sender store code).
- **Sheet Columns**:
  1. All original clearance spreadsheet columns
  2. `Status` (`<= 3m (Clearance)` or `> 3m (Rotation)`)
  3. `Suggested Receiver` (Store code or `None`)
  4. `Receiver SHD` (Numerical or `N/A`)
  5. `Suggested Transfer Qty` (Numeric)
  6. `Remark` (String)

### Styling & Aesthetics:
- **Header Formatting**: Solid Black background, White bold text, center-aligned, with Auto-Filters.
- **Auto-Width Scaling**: Auto-optimize column dimensions based on maximum content length up to a cap of 50.

## 6. Execution Command
The clearance and rotation calculation is run programmatically via:
```powershell
python scripts/clearance_rotation.py <clearance_file.xlsx> <shd_file.xlsx>
```
