---
name: Procurement Update Intelligence
description: Runs the PUR workflow against a Lark Sheet URL, builds a full Lark Doc summary, sends a short Lark IM brief, and sends a combined Section D webhook card for eligible promotions only.
---

# Procurement Update Intelligence Skill

## 1. Skill Overview
The **Procurement Update Intelligence (PUR)** skill automates the extraction, categorization, formatting, and distribution of procurement directives from a master Lark Sheet. It converts a raw procurement log into a multi-channel executive communication framework:
- **Lark Doc**: A comprehensive, detailed, permanent document of all directives.
- **Lark IM Post**: A highly condensed, bulleted summary optimized for fast mobile scanning in chat channels.
- **Section D Webhook Card**: A specialized, targeted notification card focusing strictly on promotion activities for selected outlets.

## 2. Trigger Details
- **Trigger Keywords**: `"PUR"`, `"procurement update"`, combined with a Lark Spreadsheet URL.
- **Trigger Condition**: When the keyword and a Lark URL are provided together, the agent initiates the automated extraction workflow.

## 3. Data Input Requirements
- **Lark Sheet API Access**: Active token connection to read the targeted Lark sheet URL.
- **Sheet Title Matching**:
  - The engine searches for a worksheet titled exactly `"Procurement Update"`.
  - Fallback: If not found, it parses the first visible sheet in the spreadsheet.
- **Expected Data Fields**: Columns defining procurement items, section codes (A, B, C, D, E), priorities, and outlet groups.

## 4. Detailed Business & Calculation Logic

### Category Classification Rules:
The sheet sections are mapped strictly into target categories:

| Sheet Section | Report Category | Business Mapping |
| :--- | :--- | :--- |
| **Section A** | Urgent Actions | Recalls, product returns, delist notices, emergency transfers |
| **Section B** | Inventory and Pricing | Stock status, hold purchase directives, halal updates, packaging updates, pricing adjustments |
| **Section C** | Customer and Outlet Program | Customer scripts, outlet guidance, operational procedures |
| **Section D** | Promotions and Events | Promotion execution details (filtered by outlet groups) |
| **Section E** | Competition Links | URL references to competitors (URL only, no text summary) |

### Outlet Groups Filter (Section D):
- **Eligible Outlets**: Only include promotional items matching `"BCG Outlets"` and `"Big Outlets"`.
- **Excluded Outlets**: Strictly **exclude** promotional items that are dedicated to `"Caring Outlets"` only.

### Priority Assignment Rules:
- **`critical`**: Recalls, urgent returns, deadline-enforced compliance, hold purchase directives.
- **`high`**: Halal compliance, key promo execution, gross margin or rebate changes, key packaging/stock adjustments.
- **`normal`**: Customer script templates, general reference updates, low-risk operational reminders.

## 5. Multi-Channel Output Interfaces & Formatting

### Channel 1: Lark Doc (The Master Source of Truth)
- Created using standard Markdown, formatted inside a dedicated parent folder.
- Contains sections: `Report Snapshot`, `Need Action Today`, `Urgent Actions`, `Inventory and Pricing`, `Customer and Outlet Program`, `Promotions and Events`, and `Competition Links`.
- Rendered as compact cards displaying: Status badge, priority tag, owner/department, `Why It Matters`, `Required Action`, timelines, reference links, and short `Key Notes`.

### Channel 2: Lark IM Post (The Executive Scan Brief)
- Highly condensed structure optimized for instant chat channel readability.
- Contains: Top metrics summary line, `Urgent Actions`, `Inventory and Pricing`, `Promotions`, and direct links to the full Lark Doc and source Lark Sheet.
- Text limit: Each card contains one bold headline and up to two short bullet points.

### Channel 3: Section D Webhook Card
- Send exactly **one** combined card per PUR execution run.
- Filtered to include Section D promotions for eligible outlets only. If no promotions remain after filtering, no card is sent.
- Contains: Title formatted as `Summary [DDMMYYYY]`, subject, status badge, outlet group, PIC/department, promo summary, and direct links.

### Command Execution & Platform Rules:
- Execute `lark-cli.exe` directly rather than running shell wrappers.
- Lark Doc generation MUST use the `--as user` flag.
- Lark IM Post sending MUST use the `--as bot` flag.
- The Section D Webhook Card must be POSTed to the target hook:
  `https://open.larksuite.com/open-apis/bot/v2/hook/7e308dc4-816e-4426-885e-9224bab9287d`

## 6. Execution Command
The procurement workflow is run from the workspace using:
```powershell
python scripts/execute_pur.py "<LARK_SHEET_URL>"
```
### CLI Run Arguments:
- `--doc-only`: Create the Lark Doc and local output files but skip sending IM notifications.
- `--no-webhook`: Skip sending the Section D webhook card.
