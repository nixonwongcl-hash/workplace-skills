---
name: Non Returnable Clearance
description: "Analyzes an Excel-based clearance list against SHD report to determine clearance actions and stock rotation suggestions for nearing expiration items."
---

# Non Returnable Clearance

## Overview
This skill processes a manual clearance list (provided as an Excel file) containing items that are non-returnable or nearing expiration. It maps these items against the master SHD report to generate actionable remarks for the stores, either advising them to continue selling at clearance or suggesting an optimal rotation receiver.

## Trigger
The user triggers this skill by uploading an Excel clearance list and the SHD report, along with the keyword **"non returnable clearance"**.

## Input Requirements
The user must provide:
1. **Clearance Excel File:** Must contain at least `Article No`, `Expiry (MM/YY)`, and `Qty` (Sender's Stock on Hand). The filename should preferably indicate the Sender outlet, or the user must specify it.
2. **SHD Report File:** Standard daily SHD Excel file.
3. **Sender Outlet Code:** To identify which cluster rules to apply.

## Business Logic

### Expiry Threshold
- If the expiry is **<= 3 months** away from the current date: 
  - Remark: `Continue sell under clearance price. Suggested receiver to rotate: <Receiver> (Exclude Qty. Contact receiver for consent)`
- If the expiry is **> 3 months** away:
  - Remark: `Normal rotation. Suggested receiver: <Receiver> (Transfer Qty: <X>, Receiver SHD: <Y>)`

### Cluster Transfer Rules
- **Cluster 1 Outlets:** (KKDG, KKIN, KKCM, KKGM, KKJP, KKDA, SAKN, SABF, SATR, KKLD)
  - MUST rotate **strictly** within Cluster 1.
- **Cluster 2 Outlets:** (SALD, SATW)
  - MUST prioritize rotating within Cluster 2 first. If no suitable receiver is found in Cluster 2, it can offer to Cluster 1.

### Receiver Calculation
- **Pipeline Stock** is strictly equal to **SOH** (Stock on Hand only).
- **Receiver Filter:** Only outlets with **SHD <= 30 Days** can receive.
- **Target Quantity:** Receivers will be topped up to a **120 Days Limit** based on `ceil(Daily Demand * 120 - SOH)`.
- **Sender Limit:** The final suggested transfer quantity cannot exceed the Sender's available `Qty`.

## Execution Script
The script to execute this is `scripts/clearance_rotation.py`.

```bash
python scripts/clearance_rotation.py <clearance_file.xlsx> <shd_file.xlsx> <sender_store_code>
```
