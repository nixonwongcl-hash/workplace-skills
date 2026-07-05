# Workspace Customization Rules

## Clarifying Missing Information

When executing any workspace task or processing inventory files (such as stock status checks, mass recalls, reordering calculations, supplier mapping, or stock rotation):

1. **Verify Critical Inputs First**: Before performing database/Excel lookups, file processing, or spreadsheet updates, verify that all critical parameters are present.
2. **Missing Article Codes**: 
   > [!IMPORTANT]
   > If the user provides contextual details (such as product descriptions, batch numbers, reasons, or store lists) but does **not** specify the article code(s), you **must** pause execution and ask the user to provide the exact article code(s) first. Do not make assumptions or default to guessing the code.
3. **Other Missing Context**: If crucial details required by the active skill (e.g., target stores, local supplier file path, date parameters) are missing, output a direct question to the user requesting the necessary info.
