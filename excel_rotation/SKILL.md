---
name: Excel Stock Rotation
description: Analyzes SHD Excel data to perform stock rotation based on exact fill and tiered sourcing logic. Triggered by keywords "rotate" or "rotation" along with an Excel file.
---

# Excel Stock Rotation Skill

**Trigger:** The user uploads an Excel inventory file and uses the keyword "rotate" or "rotation".

## Step 1: Mandatory Clarification
**CRITICAL:** Before processing any data or running the Excel file, you **MUST** ask the user the following 4 questions:
1. Which specific **Outlets or Pre-defined Clusters** should be included in this rotation?
   - **Pre-defined Clusters:**
     - **Cluster 1**: KKDG, KKIN, KKLD, KKCM, KKGM, KKJP, KKDA, SAKN, SABF, SATR
     - **Cluster 2**: SALD, SATW
2. **Target Coverage Limits (Defaults):** 
   - **Receivers:** Only receive if SHD <= 30 Days. Top up to 120 Days limit.
   - **Senders:** Only send if SHD > 120 Days. Keep 120 Days of supply.
   - *(Ask the user if they want to override these defaults).*
3. Do you want to filter this rotation by a **Specific Category** or analyze **All Categories**? (e.g., "MEDICINE only" or "All")
   - **Note 1 (Category):** If "MEDICINE" is selected, you MUST ask a follow-up: Should we rotate **Group B**, **Group C**, or **Both**?
   - **Note 2 (SOS):** Do you want to filter by **SOS** type? (Specify "DC", "DSP", or skip for "All")
   *Available categories for reference:*
   - BABY CARE, BEAUTY ACCESSORIES, BEAUTY SUPPLEMENT, CAMPAIGN PREMIUM, CONFECTIONARY, DENTAL ORAL & LIP CARE, DIAGNOSTIC & HEALTH AIDS, EYE, EAR & NOSE, FAMILY PLANNING, FIRST AID/SURGICAL, FOOT CARE, GENERAL PRODUCT, HAIR CARE, HEALTH FOOD & NUTRITION, HEALTH SUPPLEMENT, HEALTH SUPPLEMENT - CHILDREN, MEDICINE, MENS GROOMING, OTC MEDICINE, PERSONAL CARE, PET CARE, PREMIUM GIFT, REHABILITATION AIDS, SKIN CARE, SLIMMING & DETOX.
4. Any **Special Instructions** for custom rules rotation? (e.g., skip specific outlets as senders, or prioritize specific items)

*Wait for the user's response to these 4 questions before proceeding to Step 2.*

## Step 2: Rotation Logic & Rules
When writing or executing the Python script (`scripts/excel_rotation.py`) to process the file, ensure the following logic is strictly applied:

### Core Calculations
- **Daily Demand** = `(Day 1 to 30 + Day 31 to 60 + Day 61-90) / 90`
- **Receiver Need (`QtyNeeded`)** = `(DailyDemand * TargetDays) - SOH`.
- **Target Days (Receiver only)**: Controlled dynamically via user input (e.g., `150` days).

### Tiered Sourcing (Identifying Potential Senders)
- **Tier 1 (Dead Stock)**: `SHD == 9999`. 
  - Keep logic: Sender keeps `0` units, **unless** the `RP Type` contains the word `Forecast` (e.g., "Store SGO with Forecast"), in which case the sender keeps `1` unit.
- **Tier 2 (Slow Stock)**: `SHD >= 180`. 
  - Keep logic: Sender keeps `150` days worth of their own daily demand; anything in excess is available to send.

### Category & Classification Filtering
- If **MEDICINE** is selected, filter by the requested `PoisonClass`:
  - **Group B**: Only include items where `PoisonClass` contains "Group B".
  - **Group C**: Only include items where `PoisonClass` contains "Group C".
  - **Both**: Include items from both "Group B" and "Group C".
- **SOS Filtering (Optional)**: If specified, filter by the `SOS` column for "DC" or "DSP" matches.
- For all other categories, filter normally by the `Category` column.

### Receiving Priority
- Priority MUST be given to receiving outlets whose `OOS Indicator` is marked as "OOS".
- (Note: Do NOT enforce the historical 60-day Cool Down period as a block; instead, log all movements).

## Step 3: Output Formatting
The script must generate exactly TWO Excel output files, named with the format `DDMMYYYY`.

### File 1: `Rotation DDMMYYYY.xlsx`
Headers MUST be in this exact order:
1. **ArticleCode**
2. **ArticleDesc**
3. **Category**
4. **Reason** (e.g., "Deadstock Clearance", "Slow Stock")
5. **Sender Store**
6. **Sender SOH**
7. **Sender SHD**
8. **Receiver Store**
9. **Receiver SOH**
10. **Receiver SHD**
11. **OOS** (Convert original "OOS" string to "YES", otherwise "NO")
12. **Transfer Qty**

### File 2: `Rotation_History_Summary DDMMYYYY.xlsx`
Must contain exactly two sheets:
- **Sheet 1 ("Movement Log")**: Minimal log containing: Date, Sender Store, Receiver Store, ArticleCode, ArticleDesc, Transfer Qty
- **Sheet 2 ("Summary")**: A combined single sheet showing all aggregated reporting: 
  - Total tracked lines moved (Number of rows)
  - Total OOS lines covered
  - Total deadstock (9999) lines moved
  - **New**: Total DC lines and DSP lines
  - Summary lines statistics per Sender / Receiver outlet split into **DC** and **DSP** columns.

### Formatting Rules for Output Files
All output Excel files must apply the following formatting:
- All columns text MUST be conditionally aligned to the **center**, EXCEPT the `ArticleDesc` column which must be **aligned to the left**.
- Apply Excel data filters across all headers (except on the combined Summary sheet).
- Format the header row background to **black** and the font color to **white**.
- Auto-optimize all column widths to fit the content cleanly so it looks visually nice.

## Advanced Logic Flags (Internal)
- **`--receiver_shd_limit [Days]`**: Only consider receivers whose existing SHD is equal to or less than this value.
- **`--ignore_forecast`**: Skip the "keep 1 unit" rule for items where RP Type includes "Forecast".
