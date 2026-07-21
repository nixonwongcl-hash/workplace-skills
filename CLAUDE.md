# Workplace Skills — Project Rules

## Canonical Local Store

Use C:\Users\USER\Workplace-Skills as the only editable workplace-skill source. Agent skill folders are managed junctions to this checkout. Before execution, run the version and link audits. Never replace a managed junction with a copied folder. Automatic pulls must remain fast-forward-only and must stop on local changes.

## Mandatory Skill Version Check

The repository root is the canonical source for workplace skills. Before executing a skill, compare its `## Version` value with `skill_versions.json`. If the working or installed copy is older, missing, or unversioned, refresh it from the canonical root before running it.

Validate with `python scripts/verify_skill_versions.py`.

## Clarifying Missing Information

When executing any workspace task or processing inventory files (such as stock status checks, mass recalls, reordering calculations, supplier mapping, or stock rotation):

1. **Verify Critical Inputs First**: Before performing database/Excel lookups, file processing, or spreadsheet updates, verify that all critical parameters are present.

2. **Missing Article Codes**:
   - If the user provides contextual details (such as product descriptions, batch numbers, reasons, or store lists) but does **not** specify the article code(s), you **must** pause execution and ask the user to provide the exact article code(s) first.
   - Do **not** make assumptions or attempt to guess article codes from descriptions alone.

3. **Other Missing Context**: If crucial details required by the active skill (e.g., target stores, local supplier file path, date parameters) are missing, ask the user directly before proceeding.

## Skills Overview

This workspace contains agent skills for East Malaysia pharmacy inventory management:

| Skill | Trigger Keywords | Purpose |
|---|---|---|
| `article_check_recall_return` | `check article`, `mass recall`, `recall report` | SOH check or mass recall report from SHD Excel |
| `reorder_suggested_qty` | `calculate reorder`, `reorder qty` | Reorder calculations using Pareto strategies |
| `shd_stock_rotation` | `rotate`, `rotation` | Stock rotation based on tiered sourcing logic |
| `match_local_supplier` | `match local supplier` | Map reorder list against local ordering file |
| `non_returnable_clearance_form_remark` | `non returnable clearance` | Clearance list analysis vs SHD data |
| `shd_pareto_mapping` | `pareto mapping` | Map Pareto sales data into SHD report |
| `pwp_analysis` | `pwp`, `pwp performance` | PWP Receipt Count performance reports |
| `pbo_gp_analysis` | `pbo gp`, `gp penetration` | PBO margin data analysis |
| `procurement_update` | `procurement update` | PUR workflow against Lark Sheet URL |

## Key File Paths

- **SHD Report**: Usually located at `C:\Users\USER\Downloads\SHD <DDMMYYYY>.xlsx`
- **Output Directory**: Workspace root and `C:\Users\USER\Downloads\`
- **Local Supplier File**: `C:\Users\USER\Downloads\<region> POISON <date>.xlsx`
