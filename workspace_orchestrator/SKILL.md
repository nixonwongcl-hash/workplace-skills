---
name: Workspace Orchestrator
description: Unified entry point (Option 1 & 2) that auto-detects spreadsheet schemas to identify candidate workplace skills and displays an interactive menu in chat.
---

# Workspace Orchestrator Skill

## 1. Skill Overview
The **Workspace Orchestrator** is a unified command hub designed to eliminate trigger keyword memorization. It integrates **Option 1 (Interactive Selection Menu)** and **Option 2 (Zero-Keyword Auto-Detection)** into a single streamlined operations framework. When triggered, it analyzes spreadsheets in the workspace and Downloads folder, identifies the structure of the data, and displays recommendations and direct action menus.

## 2. Trigger Details
- **Trigger Keywords**: `"run skill"`, `"workspace"`, `"process"`, `"process this"`, `"orchestrate"`, or when any generic spreadsheet (`.xlsx`, `.xlsm`, `.xls`, `.csv`) is uploaded without specific instructions.
- **Trigger Condition**: When these keywords are triggered or an unannotated spreadsheet is uploaded, this skill executes.

## 3. Operations Workflow for the Agent

### Step 1: Execute Auto-Detection Engine
Run the background signature parsing tool at the root of the workspace:
```powershell
python scripts/orchestrator.py
```
This script returns a JSON payload listing recent spreadsheets, their sheet tabs, their columns, and matched candidate skills.

### Step 2: Render the Premium Interactive Menu
Analyze the JSON payload and render a stunning, high-readability Markdown response in the chat:
1. **Auto-Detected Files (Option 2)**: List the detected spreadsheets and their recommended skill actions.
2. **Standard Skills Library (Option 1)**: Present a numbered menu of all 8 available workplace skills so the user can manually route files or force-run specific routines.

#### Layout Example:
> 🎯 **Workspace Orchestrator**
> 
> I have scanned your workspace and Downloads folders for recent spreadsheet data:
> 
> ### 🔍 Auto-Detected Recommendations (Option 2)
> - 📂 **`SHD 22052026.xlsx`** (Downloads)
>   *   *Columns detected*: `SOH`, `Store`, `ArticleCode`, `Day 1 to 30`
>   *   *Recommended Action*: 📈 **Excel Reorder Calculation** or 🚚 **Excel Stock Rotation**
> - 📂 **`PWP_Raw_Data.csv`** (Downloads)
>   *   *Columns detected*: `SiteCodeName`, `SalesmanName`, `PWP Receipt Count`
>   *   *Recommended Action*: 📊 **PWP Performance Analysis**
> 
> ---
> 
> ### 🛠️ Workplace Skills Library Menu (Option 1)
> If you'd like to force-run a specific analysis, please reply with the corresponding number:
> 1.  📊 **PWP Performance Analysis** (`pwp_analysis`)
> 2.  📈 **Excel Reorder Calculation** (`excel_reorder`)
> 3.  🚚 **Excel Stock Rotation** (`excel_rotation`)
> 4.  🔬 **Non-Returnable Clearance Audit** (`non_returnable_clearance`)
> 5.  🤝 **Match Local Supplier** (`match_local_supplier`)
> 6.  🔍 **Check Article / Mass Recall** (`check_article`)
> 7.  🗺️ **Excel Pareto Mapping** (`excel_pareto_mapping`)
> 8.  📢 **Procurement Update (PUR)** (`procurement_update`)
> 
> **How would you like to proceed?** (e.g. reply *"Run 2 on SHD"* or *"Yes, run PWP"*)

### Step 3: Execute the Chosen Skill
Once the user confirms the selection, execute the corresponding sub-skill CLI command directly as documented in their individual `SKILL.md` profiles.
