# 🛠️ Workplace Skills Repository

Welcome to the **Workplace Skills** repository! This repository is a centralized, production-grade library of custom automation scripts and agentic skills designed to optimize inventory replenishment, stock balancing, regional supplier mapping, and sales performance analysis.

These skills are structured to be executed seamlessly by both developers and AI agent assistants, utilizing high-performance data processing frameworks (`pandas`, `calamine`, `openpyxl`, `xlsxwriter`) to manipulate complex multi-sheet Excel files.

---

## 📋 Directory of Available Skills

This repository contains **8 core skills** optimized for automated logistics, procurement, and operations:

| Skill Folder | Skill Name | Trigger Keywords | Primary Business Function |
| :--- | :--- | :--- | :--- |
| [📁 `check_article`](./check_article) | **Check Article** | `"check article"`, `"recall report"`, `"soh check"` | Isolates active stock levels (SOH > 0) of specific articles across retail outlets for sweeps or mass recalls. |
| [📁 `excel_pareto_mapping`](./excel_pareto_mapping) | **Excel Pareto Mapping** | `"map pareto"`, `"map sales data to shd"` | Maps sales quantities, amounts, and Pareto classifications from sales histories into Stock on Hand (SHD) reports. |
| [📁 `excel_reorder`](./excel_reorder) | **Excel Reorder Calculation** | `"calculate reorder"`, `"reorder qty"`, `"reorder"` | Implements 4 distinct Pareto-driven replenishment models, rounding quantities to Target Reorder Pack sizes (TRP). |
| [📁 `excel_rotation`](./excel_rotation) | **Excel Stock Rotation** | `"rotate"`, `"rotation"`, `"stock rotation"` | Automates stock rebalancing from overstocked "Senders" to understocked "Receivers" within geographical clusters. |
| [📁 `match_local_supplier`](./match_local_supplier) | **Match Local Supplier** | `"match local supplier"`, `"map supplier"` | Restricts reorder items to prescription medicines, appends local vendor information/costs, and calculates 30-day top-ups. |
| [📁 `non_returnable_clearance`](./non_returnable_clearance) | **Non Returnable Clearance** | `"non returnable clearance"` | Audits manual clearance lists of near-expiry stocks against SHD reports to suggest pricing actions or rotation routes. |
| [📁 `procurement_update`](./procurement_update) | **Procurement Update Intelligence** | `"PUR"`, combined with Lark Sheet URL | Pulls log entries from Lark Sheets, maps item priorities, and sends automated summaries to Lark Docs, IMs, and webhooks. |
| [📁 `pwp_analysis`](./pwp_analysis) | **PWP Performance Analysis** | `"analyse pwp"`, `"pwp performance"` | Splits raw Purchase With Purchase transactions by site, pivots daily performance, ranks salesmen, and highlights outliers. |

---

## 🔄 Automated Operations Workflow

These skills are designed to function together as an integrated replenishment and balancing pipeline:

```mermaid
graph TD
    A[Raw Sales Report] -->|1. Pareto Mapping| B(Mapped SHD Master Report)
    B -->|2. Reorder Calculation| C(Suggested Reorder List)
    C -->|3. Supplier Matching| D(Local Supplier Purchase Proposals)
    B -->|4. Stock Rotation| E(Inter-store Transfer Files)
    F[Manual Clearance List] -->|5. Clearance Analysis| G(Clearance Remarks & Transfers)
```

1. **Pareto Sales Mapping**: Standardizes site details and maps historical sales into the master SHD report.
2. **Reorder Engine**: Applies daily demand formulas and pipeline stocks to propose rounded top-ups (applying Red/Orange/Yellow visual flags).
3. **Local Supplier Matching**: Segregates prescription drugs and maps them to local suppliers for Sabah ordering.
4. **Stock Rotation**: Identifies dead/slow stocks at overstocked Senders and moves them to understocked Receivers.
5. **Clearance sweeps**: Generates expiry-based remarks and routes eligible near-expiry stocks to active retail hubs.

---

## ⚙️ Technical Requirements

The scripts in this repository rely on Python 3.10+ and a set of highly optimized spreadsheet manipulation libraries.

### Core Dependencies:
- **`pandas`**: High-performance data structures and data cleaning.
- **`openpyxl`**: Writing styled spreadsheet workbooks, cell formatting, and alignment adjustments.
- **`xlsxwriter`**: High-efficiency multi-tab writing and advanced conditional cell color formatting.
- **`python-calamine`**: Low-level Rust-based calamine engine for extremely fast reading of large `.xlsx` files.

### Standard Installation:
Ensure the required libraries are installed before running any skill:
```bash
pip install pandas openpyxl xlsxwriter python-calamine
```

---

## 🚀 Execution & Troubleshooting

Detailed instructions for running, parameterizing, and customizing each skill are documented inside their respective subfolders. Please navigate to each skill's directory and read its **`SKILL.md`** file for precise CLI syntaxes, flag descriptions, and custom options.
