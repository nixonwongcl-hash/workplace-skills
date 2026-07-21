---
name: shd-stock-rotation
description: Analyzes SHD Excel data to perform stock rotation based on exact fill and tiered sourcing logic. Triggered by keywords "rotate" or "rotation" along with an Excel file.
---

# SHD Stock Rotation Skill

## Version
Current version: **v1.0.0** (2026-07-21)

## 1. Skill Overview
The **SHD Stock Rotation** skill automates the redistribution of slow-moving or excess inventory to understocked or out-of-stock retail outlets. Operating within pre-defined geographical or operational store clusters, the rotation engine identifies high-stock "Senders" and low-stock "Receivers". By balancing inventory levels, the skill minimizes waste, mitigates out-of-stock (OOS) conditions, and avoids redundant procurement.

## 2. Trigger Details
- **Trigger Keywords**: `"rotate"`, `"rotation"`, `"stock rotation"`, `"inventory balancing"`.
- **Trigger Condition**: Upload of a master SHD inventory Excel report alongside the keywords.

## 3. Mandatory Setup Questions
Before running the rotation calculations, you **MUST** present these 4 setup questions to the user and wait for their explicit input:
1. **Outlets or Pre-defined Clusters**: Which specific outlets or clusters should be included?
   - **Cluster 1**: `KKDG`, `KKIN`, `KKLD`, `KKCM`, `KKGM`, `KKJP`, `KKDA`, `SAKN`, `SABF`, `SATR`
   - **Cluster 2**: `SALD`, `SATW`
2. **Target Coverage Limits (Defaults)**:
   - **Receivers**: Accept stock only if `SHD <= 30 Days`. Top up to `120 Days` of supply.
   - **Senders**: Send stock only if `SHD > 120 Days`. Retain a minimum of `120 Days` of supply.
   - *Ask the user if they wish to override these default limits.*
3. **Category & Classification Filtering**:
   - Do you want to filter by a **Specific Category** (e.g. `"MEDICINE only"`) or analyze **All Categories**?
     - *If "MEDICINE" is selected, follow up*: Should we rotate **Group B**, **Group C**, or **Both** Poison Classes?
     - *If SOS filtering is desired*: Should we filter by **SOS** type (`"DC"`, `"DSP"`, or `"All"`)?
4. **Special Instructions**: Are there any custom rules to apply? Select all that apply:
   - **Priority Sender Outlet**: Force maximum rotation *out* of a specific store for a given brand or subcategory (e.g., *"Maximise rotation out of KKDA for Lily Ba brand and COSMETICS-LIP & ORAL-LIP CARE subcategory"*).
   - **Skip Sender Stores**: Exclude specific outlets from acting as senders entirely.
   - **Priority Receiver Stores**: Give certain outlets first pick when receiving stock.
   - **Custom rules**: Any other bespoke logic (describe in free text).
5. **Subcategory Exclusions**: Are there any subcategories that should be **completely excluded** from rotation (neither sent nor received)?
   - **REHAB Standard Exclusion** *(pre-defined)*: Exclude all rows where `SubCategory` is any of:
     - `REHAB-HOSP BED/ACCS`
     - `REHAB-L/WT WHEELCHR`
     - `REHAB-COMMODE CHAIR`
     - `REHAB-SP WHEELCHAIR`
     - `REHAB-STD WHEELCHAIR`
   - **Custom Exclusions**: Specify any additional subcategories to exclude.
   - *If no exclusions are needed, answer "None".*

## 4. Detailed Business & Calculation Logic
1. **Daily Demand Calculation**:
   - `Daily Demand = (Day 1 to 30 + Day 31 to 60 + Day 61-90) / 90`
2. **Receiver Need (`QtyNeeded`)**:
   - `QtyNeeded = (Daily Demand * TargetDays) - SOH` where `TargetDays` is the top-up limit (default: 120).
3. **Tiered Senders Sourcing**:
   - **Tier 1 (Dead Stock)**: Identified by `SHD == 9999`.
     - Senders keep `0` units, **except** when `RP Type` contains the word `Forecast` (e.g. `"Store SGO with Forecast"`), in which case the sender must retain exactly `1` unit as safety stock.
   - **Tier 2 (Slow Stock)**: Identified by `SHD >= 180`.
     - Senders keep `150` days worth of their own daily demand (`150 * Daily Demand`); any inventory in excess of this keep limit is available to rotate.
4. **Category & Poison Filtering**:
   - If **MEDICINE** is targeted, filter by `PoisonClass` using exact substring matches:
     - **Group B**: Only rows where `PoisonClass` contains `"Group B"`.
     - **Group C**: Only rows where `PoisonClass` contains `"Group C"`.
     - **Both**: Include both Group B and Group C items.
   - **SOS Type Matching**: If specified, filter strictly by the `SOS` column (`"DC"` or `"DSP"`).
5. **Receiving Priority**:
   - Priority is given to receiving outlets whose `OOS Indicator` is marked as `"OOS"`.
6. **Movements**: Keep a comprehensive log of all suggested transfers even if within cool-down periods.

## 5. Output Structure & Formatting Standards
The engine generates exactly two output Excel files, saved locally using the date format `DDMMYYYY`:

### File 1: `Rotation DDMMYYYY.xlsx`
Contains the detailed transfer instructions. Column order is strictly:
1. `ArticleCode` (Center-aligned)
2. `ArticleDesc` (Left-aligned)
3. `Category` (Center-aligned)
4. `Reason` (e.g., `"Deadstock Clearance"`, `"Slow Stock"`)
5. `Sender Store` (Center-aligned)
6. `Sender SOH` (Center-aligned)
7. `Sender SHD` (Center-aligned)
8. `Receiver Store` (Center-aligned)
9. `Receiver SOH` (Center-aligned)
10. `Receiver SHD` (Center-aligned)
11. `OOS` (Convert original `"OOS"` string to `"YES"`, otherwise `"NO"`)
12. `Transfer Qty` (Center-aligned)

### File 2: `Rotation_History_Summary DDMMYYYY.xlsx`
Contains two sheets:
- **Sheet 1 (`Movement Log`)**: A flat audit trail containing columns: `Date`, `Sender Store`, `Receiver Store`, `ArticleCode`, `ArticleDesc`, `Transfer Qty`.
- **Sheet 2 (`Summary`)**: Executive metrics showing:
  - Total rows moved.
  - Total OOS lines covered.
  - Total deadstock (`9999`) lines moved.
  - Total `DC` lines and `DSP` lines.
  - Pivot table of sender/receiver outlet splits divided into distinct `DC` and `DSP` quantity columns.

### Styling & Aesthetics:
- **Header Row Style**: Solid Black background, White bold text, center-aligned.
- **Data Alignments**: Center-aligned for all columns except `ArticleDesc`, which is left-aligned.
- **Auto-Filter**: Enabled on all column headers (except the summary pivot sheet).
- **Auto-Width**: Auto-adjust column widths based on maximum content length + 2 padding.

## 6. Execution Command
The python rotation engine is run from the workspace using the following command:
```powershell
python .agent/skills/shd_stock_rotation/scripts/excel_rotation.py
```
### Advanced CLI Flags:
- `--receiver_shd_limit [Days]`: Set strict receiving SHD limits (e.g., `--receiver_shd_limit 30`).
- `--ignore_forecast`: Skip the safety "keep 1 unit" rule for forecast-enabled Senders.
- `--skip_sender_stores [STORE_CODES]`: Comma-separated store codes to exclude as senders.
- `--priority_receivers [STORE_CODES]`: Comma-separated store codes to prioritise as receivers.
- `--skip_receiver_stores [STORE_CODES]`: Comma-separated store codes to exclude as receivers.

## 7. Special Instruction Patterns

### REHAB Subcategory Exclusion *(Standard Practice)*
When the user requests REHAB exclusion (Q5), filter out all rows where `SubCategory` exactly matches any of the REHAB entries **before** running the rotation engine. This applies to both sender and receiver pools.

### Priority Sender Outlet (e.g., KKDA Maximise)
When a store is flagged as a priority sender for a specific **brand** or **subcategory**:
- Override the standard SHD threshold — rotate out regardless of whether SHD meets the ≥ 120 threshold.
- Keep logic: retain `0` units (or `1` if RP Type contains `"Forecast"`).
- Tag these transfers with `Reason = "KKDA Priority Clearance"` (or similar outlet-specific label) in the output.
- This is applied **per article** — only rows matching the brand/subcategory filter at that outlet are affected; other articles at the same outlet follow standard rules.
