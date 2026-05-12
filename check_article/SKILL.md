---
name: Check Article
description: Generates a stock on hand (SOH) check or mass recall report for a specific list of articles using SHD Excel data. Triggered by keyword "check article".
---

# Check Article Skill

**Trigger:** The user uploads an Excel inventory file, provides a list of article codes, and uses the keyword "check article".

## Step 1: Processing the Data
When writing or executing the Python script to process the file, ensure the following logic is strictly applied:
1. Filter the dataset for the provided `ArticleCode` list.
2. Only include rows where `SOH > 0`.

## Step 2: Output Formatting
The script must generate an Excel output file named with the format `Recall_Report_DDMMYYYY.xlsx` or `Article_Check_DDMMYYYY.xlsx`.

Headers MUST be in this exact order:
1. **ArticleCode**
2. **ArticleDesc**
3. **Category**
4. **Reason** (Default to "Mass Recall" or "Article Check" depending on context)
5. **Sender Store** (Maps to the 'Store' column in the raw data)
6. **Sender SOH** (Maps to the 'SOH' column in the raw data)

*Note: Do NOT include Sender SHD, Receiver Store, Receiver SOH, Receiver SHD, OOS, or Transfer Qty. This report is strictly for checking SOH at stores.*

### Formatting Rules for Output Files
All output Excel files must apply the following formatting:
- All columns text MUST be conditionally aligned to the **center**, EXCEPT the `ArticleDesc` column which must be **aligned to the left**.
- Apply Excel data filters across all headers.
- Format the header row background to **black** and the font color to **white**.
- Auto-optimize all column widths to fit the content cleanly so it looks visually nice.
