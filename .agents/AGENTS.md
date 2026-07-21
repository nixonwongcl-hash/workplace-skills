# Workspace Customization Rules

## Canonical Local Store

Use C:\Users\USER\Workplace-Skills as the only editable workplace-skill source. Agent skill folders are managed junctions to this checkout. Before execution, run the version and link audits. Never replace a managed junction with a copied folder. Automatic pulls must remain fast-forward-only and must stop on local changes.

## Mandatory Skill Version Check

The repository root is the only canonical skill source. Before using a workplace skill:

1. Read `skill_versions.json` at the repository root.
2. Compare its version with the `## Version` value in the selected local `SKILL.md`.
3. If the local copy is older or has no version, do not run it. Refresh it from the canonical root first.
4. Never treat `.agents/skills/` or another copied skill directory as newer without comparing versions.

Run `python scripts/verify_skill_versions.py` to validate the canonical checkout. Use `--installed-root <path>` to validate installed copies. Refresh stale copies with `python scripts/sync_skill_versions.py --target <skills-root>`.

## Clarifying Missing Information

When executing any workspace task or processing inventory files (such as stock status checks, mass recalls, reordering calculations, supplier mapping, or stock rotation):

1. **Verify Critical Inputs First**: Before performing database/Excel lookups, file processing, or spreadsheet updates, verify that all critical parameters are present.
2. **Missing Article Codes**:
   > [!IMPORTANT]
   > If the user provides contextual details (such as product descriptions, batch numbers, reasons, or store lists) but does **not** specify the article code(s), you **must** pause execution and ask the user to provide the exact article code(s) first. Do not make assumptions or default to guessing the code.
3. **Other Missing Context**: If crucial details required by the active skill (e.g., target stores, local supplier file path, date parameters) are missing, output a direct question to the user requesting the necessary info.
