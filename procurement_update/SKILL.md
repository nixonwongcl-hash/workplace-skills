---
name: Procurement Update Intelligence
description: Runs the PUR workflow against a Lark Sheet URL, builds a full Lark Doc summary, sends a short Lark IM brief, and sends a combined Section D webhook card for eligible promotions only.
---

# Procurement Update Intelligence

Trigger this skill when the user provides a Lark Sheet URL together with the keyword `PUR`.

## Goal
Produce a procurement update that is easy to read in three places:
- A **Lark Doc** with a full summary and detailed operational notes.
- A **Lark IM post** with only the most important items for fast scanning in chat.
- A **Section D webhook card** for promotion activities and awareness campaigns only.

## Source Of Truth
Use the workspace runner:

```powershell
python C:\Users\USER\.gemini\antigravity\playground\azure-radiation\scripts\execute_pur.py "<SHEET_URL>"
```

For report generation without IM sending:

```powershell
python C:\Users\USER\.gemini\antigravity\playground\azure-radiation\scripts\execute_pur.py "<SHEET_URL>" --doc-only
```

## Workflow
1. Resolve spreadsheet metadata first with `sheets +info --url`.
2. Identify the main worksheet by title match to `Procurement Update`, then fall back to the first visible sheet if needed.
3. Read the data by `sheet_id` and real worksheet row count.
4. Parse rows into normalized procurement items.
5. Rank each item by category and priority.
6. Render:
   - `pur_report.md`
   - `pur_highlights.json`
   - `pur_items.json`
   - `pur_sections.json`
   - `pur_sheet_raw.json`
7. Create the Lark Doc as `user`.
8. Send the short Lark IM post as `bot`.
9. Send one combined Section D webhook card when eligible items exist.

## Category Rules
Map source sections into business-facing categories:

| Sheet Section | Report Category | Notes |
|---|---|---|
| A | Urgent Actions | recalls, returns, delist, transfer |
| B | Inventory and Pricing | stock, hold purchase, halal, packaging, pricing |
| C | Customer and Outlet Program | selling points, outlet guidance |
| D | Promotions and Events | only include `BCG Outlets` and `Big Outlets`; exclude `Caring Outlets`-only items |
| E | Competition Links | URL only, no content summary |

## Priority Rules
- `critical`: recalls, urgent returns, deadlines, hold purchase items
- `high`: halal/compliance updates, promo execution, margin or rebate changes, key packaging or stock changes
- `normal`: selling scripts, reference-only updates, lower-risk reminders

## Output Interface

### Lark Doc
The doc should be the full source of truth:
- `Report Snapshot`
- `Need Action Today`
- `Urgent Actions`
- `Inventory and Pricing`
- `Customer and Outlet Program`
- `Promotions and Events`
- `Competition Links`

Each item should be rendered as a compact card:
- subject with status badge
- priority
- owner, department, group
- `Why It Matters`
- `Required Action`
- timeline when present
- direct reference link
- short `Key Notes`

### Lark IM Post
The IM should be shorter than the doc and optimized for chat:
- top stats line
- `Urgent Actions`
- `Inventory and Pricing`
- `Promotions`
- link to full report
- link to source sheet

Each IM item should contain:
- one bold headline
- up to two short bullets
- a direct link when available

### Section D Webhook Card
- Send one combined card per PUR run.
- Only include Section D items after outlet filtering.
- If no eligible Section D items remain, send nothing.
- The card title must include `Summary` and date in `DDMMYYYY`.
- Include subject, status, outlet group, PIC/department, short promo details, and any direct link.

## Command And Identity Rules
- Call `lark-cli.exe` directly, not the `.cmd` wrapper.
- Create docs with `--as user`.
- Send IM posts with `--as bot`.
- Send the Section D webhook card to:
  `https://open.larksuite.com/open-apis/bot/v2/hook/7e308dc4-816e-4426-885e-9224bab9287d`
- Do not pass large JSON through shell string interpolation when avoidable. Prefer reading highlight data from file or passing Python objects directly.

## Important Notes
- Section E is always URL-only.
- If a Google reference requires authentication, keep the URL and let the report stand on the sheet-provided detail text.
- The output should prioritize scanability over completeness in the IM post.
- The Lark Doc is the detailed source of truth; the IM is the decision brief.
