import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

LARK_CLI = r"C:\Users\USER\AppData\Roaming\npm\node_modules\@larksuite\cli\bin\lark-cli.exe"
BOT_USER_ID = "ou_38cc115ab85ef101ee7a9be0d753e29a"
DRIVE_FOLDER_TOKEN = "Oq2yfmLA5lmzMQdU9gMjriV0pgd"
SECTION_D_WEBHOOK_URL = "https://open.larksuite.com/open-apis/bot/v2/hook/7e308dc4-816e-4426-885e-9224bab9287d"
MAIN_TAB_HINT = "procurement update"
BASE_DIR = Path(__file__).resolve().parent.parent

SECTION_LABELS = {
    "urgent": "Urgent Actions",
    "inventory_pricing": "Inventory and Pricing",
    "program": "Customer and Outlet Program",
    "promotion": "Promotions and Events",
    "competition": "Competition Links",
}

SECTION_ORDER = [
    "urgent",
    "inventory_pricing",
    "program",
    "promotion",
    "competition",
]

PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2}
STATUS_ORDER = {"New": 0, "Reminder": 1}


@dataclass
class ProcurementItem:
    source_section: str
    category: str
    priority: str
    status: str
    subject: str
    group: str
    pic: str
    department: str
    reference_label: str
    reference_url: str
    detail_lines: list[str]
    why_it_matters: str
    required_action: str
    due_note: str
    im_headline: str
    im_bullets: list[str]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r", "")
    for _ in range(2):
        if any(mark in text for mark in ("â", "ð", "Î", "Γ")):
            repaired = None
            for source_encoding in ("cp1252", "latin1"):
                try:
                    repaired = text.encode(source_encoding).decode("utf-8")
                    break
                except (UnicodeDecodeError, UnicodeEncodeError):
                    continue
            if not repaired or repaired == text:
                break
            text = repaired
    replacements = {
        "â€“": "-",
        "â€”": "-",
        "â€™": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€": '"',
        "â€": '"',
        "â†’": "->",
        "âœ…": "[OK]",
        "âœ”": "[OK]",
        "â€¢": "-",
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "→": "->",
        "✅": "[OK]",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_detail_lines(text: str) -> list[str]:
    if not text:
        return []
    prepared = normalize_text(text)
    markers = [
        "Affected batch:",
        "Recall reason:",
        "Action required from outlets:",
        "Submission deadline:",
        "Take note:",
        "Alternative Brand:",
        "Actions Required:",
        "How to Sell Together",
        "Bundle Pitch",
        "Why Bundle?",
        "Upselling Tips:",
        "Goal:",
        "Items involved:",
        "Exclusivity:",
        "Support:",
        "Product Positioning:",
        "Best for:",
        "How to Use",
        "Selling Script:",
        "Target Customers:",
        "PROMOTION MECHANISM:",
        "PROMOTION PERIOD:",
        "Important notes:",
    ]
    for marker in markers:
        prepared = prepared.replace(marker, f"\n{marker}")

    # Break compact numbered instructions into separate lines.
    prepared = re.sub(r"(?<=\D)(\d+)\.\s*", r"\n\1. ", prepared)
    prepared = re.sub(r"(?<=:)(\d+)\.\s*", r"\n\1. ", prepared)
    prepared = re.sub(r"(?<=[a-zA-Z])(\d+\))\s*", r"\n\1 ", prepared)

    parts: list[str] = []
    for raw_line in prepared.split("\n"):
        line = normalize_text(raw_line).strip("- ").strip()
        if not line:
            continue
        if re.fullmatch(r"\d+\.", line):
            continue
        if len(line) > 240 and ". " in line:
            sentence_parts = [normalize_text(p) for p in re.split(r"(?<=[.!?])\s+", line) if normalize_text(p)]
            parts.extend(sentence_parts)
        else:
            parts.append(line)
    return parts


def extract_text_and_link(cell: Any) -> tuple[str, str]:
    if not cell:
        return "", ""
    if isinstance(cell, list):
        text = "".join(item.get("text", "") for item in cell)
        link = ""
        for item in cell:
            if item.get("link"):
                link = item["link"]
                break
        return normalize_text(text), normalize_text(link)
    return normalize_text(cell), ""


def run_lark_cli(args: list[str]) -> dict[str, Any]:
    cmd = [LARK_CLI, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "lark-cli command failed")

    raw_stdout = result.stdout.strip()
    if "_notice" in raw_stdout:
        first_brace = raw_stdout.find("{")
        if first_brace != -1:
            raw_stdout = raw_stdout[first_brace:]
    payload = json.loads(raw_stdout)
    if not payload.get("ok"):
        error = payload.get("error", {}).get("message", "Unknown Lark API error")
        raise RuntimeError(error)
    return payload


def get_sheet_info(sheet_url: str) -> dict[str, Any]:
    return run_lark_cli(["sheets", "+info", "--url", sheet_url, "--as", "bot"])


def resolve_main_sheet(sheet_url: str) -> dict[str, Any]:
    info = get_sheet_info(sheet_url)
    sheets = info["data"]["sheets"]["sheets"]
    main_sheet = None
    for sheet in sheets:
        title = normalize_text(sheet.get("title", "")).lower()
        if MAIN_TAB_HINT in title:
            main_sheet = sheet
            break
    if not main_sheet and sheets:
        main_sheet = sheets[0]
    if not main_sheet:
        raise RuntimeError("No worksheet found in spreadsheet metadata")
    spreadsheet = info["data"]["spreadsheet"]["spreadsheet"]
    return {
        "spreadsheet_token": spreadsheet["token"],
        "spreadsheet_title": normalize_text(spreadsheet["title"]),
        "sheet_id": main_sheet["sheet_id"],
        "sheet_title": normalize_text(main_sheet["title"]),
        "row_count": int(main_sheet["grid_properties"]["row_count"]),
    }


def read_sheet_values(sheet_url: str, sheet_id: str, row_count: int) -> dict[str, Any]:
    read = run_lark_cli(
        [
            "sheets",
            "+read",
            "--url",
            sheet_url,
            "--sheet-id",
            sheet_id,
            "--range",
            f"A1:G{row_count}",
            "--as",
            "bot",
        ]
    )
    return read


def parse_sections(values: list[list[Any]]) -> dict[str, list[dict[str, Any]]]:
    sections: dict[str, list[dict[str, Any]]] = {}
    current_section = None

    for row in values:
        if not row:
            continue
        section_label, _ = extract_text_and_link(row[0] if len(row) > 0 else None)
        if section_label and len(section_label) == 1 and section_label.isalpha():
            current_section = section_label.upper()
            sections.setdefault(current_section, [])
            continue

        if not current_section:
            continue

        status, _ = extract_text_and_link(row[1] if len(row) > 1 else None)
        if status in {"New", "New ", "Reminder"}:
            subject, _ = extract_text_and_link(row[2] if len(row) > 2 else None)
            group, _ = extract_text_and_link(row[3] if len(row) > 3 else None)
            pic, _ = extract_text_and_link(row[4] if len(row) > 4 else None)
            department, _ = extract_text_and_link(row[5] if len(row) > 5 else None)
            ref_label, ref_link = extract_text_and_link(row[6] if len(row) > 6 else None)
            sections[current_section].append(
                {
                    "status": normalize_text(status),
                    "subject": subject,
                    "group": group,
                    "pic": pic,
                    "department": department,
                    "reference_label": ref_label,
                    "reference_url": ref_link,
                    "detail_lines": [],
                }
            )
            continue

        if len(row) > 2 and row[2] and sections.get(current_section):
            detail_text, detail_link = extract_text_and_link(row[2])
            if detail_text:
                sections[current_section][-1]["detail_lines"].extend(split_detail_lines(detail_text))
            if detail_link and not sections[current_section][-1]["reference_url"]:
                sections[current_section][-1]["reference_url"] = detail_link
    return sections


def summarize_detail(detail_lines: list[str], fallback: str) -> str:
    for line in detail_lines:
        lowered = line.lower()
        if lowered.startswith("action required") or lowered.startswith("submission deadline"):
            continue
        if len(line) >= 18:
            return line.rstrip(".")
    return fallback


def extract_deadline(detail_lines: list[str]) -> str:
    for line in detail_lines:
        lowered = line.lower()
        if "deadline" in lowered:
            return line.replace("Submission deadline:", "").strip()
        if "effective" in lowered:
            return line.strip()
    return ""


def infer_priority(subject: str, details: list[str], source_section: str) -> str:
    haystack = f"{subject} {' '.join(details)}".upper()
    if any(keyword in haystack for keyword in ["URGENT", "RECALL", "MASS RETURN", "DEADLINE", "HOLD PURCHASE"]):
        return "critical"
    if any(keyword in haystack for keyword in ["HALAL", "RESUMPTION", "STICKER", "MARGIN", "PROMOTION", "REBATE", "PACKAGING", "BO MASS"]):
        return "high"
    if source_section == "D":
        return "high"
    return "normal"


def infer_category(source_section: str, subject: str, details: list[str]) -> str:
    haystack = f"{subject} {' '.join(details)}".upper()
    if source_section == "A":
        return "urgent"
    if source_section == "B":
        return "inventory_pricing"
    if source_section == "C":
        return "program"
    if source_section == "D":
        return "promotion"
    if source_section == "E":
        return "competition"
    if "PROMO" in haystack or "PROMOTION" in haystack:
        return "promotion"
    return "inventory_pricing"


def infer_action(subject: str, details: list[str], source_section: str) -> str:
    text = f"{subject} {' '.join(details)}".lower()
    if "recall" in text:
        return "Process the affected returns immediately and follow the recall workflow."
    if "hold purchase" in text:
        return "Hold normal purchase orders and use urgent PR only for genuine demand."
    if "halal" in text and "sticker" in text:
        return "Apply the correction sticker before resuming shelf display and sales."
    if "halal" in text:
        return "Clarify the halal status to customers and keep the approved reference on hand."
    if "packaging" in text:
        return "Use the updated packaging reference when checking stock and answering outlet questions."
    if source_section == "D":
        return "Execute the promo mechanics in-store and display the required promo material."
    if source_section == "C":
        return "Use the selling points and script during outlet or customer engagement."
    return "Monitor the update and follow the linked reference for operational detail."


def build_im_bullets(why: str, action: str, due_note: str) -> list[str]:
    bullets = [why]
    if action and action != "Monitor":
        bullets.append(action)
    if due_note:
        bullets.append(f"Timeline: {due_note}")
    return bullets[:2]


def build_items(sections: dict[str, list[dict[str, Any]]]) -> list[ProcurementItem]:
    items: list[ProcurementItem] = []
    for source_section, raw_items in sections.items():
        for raw in raw_items:
            group = normalize_text(raw["group"])
            if source_section in {"D", "E"} and "BCG" not in group and "Big" not in group:
                continue
            if source_section == "D" and "Caring" in group and "BCG" not in group and "Big" not in group:
                continue

            detail_lines = [normalize_text(line) for line in raw["detail_lines"] if normalize_text(line)]
            subject = normalize_text(raw["subject"])
            reference_label = normalize_text(raw["reference_label"])
            reference_url = normalize_text(raw["reference_url"])
            if reference_label.upper() == "NO":
                reference_label = ""
            if not reference_label and reference_url:
                reference_label = "Direct reference"
            category = infer_category(source_section, subject, detail_lines)
            priority = infer_priority(subject, detail_lines, source_section)
            why_it_matters = summarize_detail(detail_lines, subject)
            required_action = infer_action(subject, detail_lines, source_section)
            due_note = extract_deadline(detail_lines)
            im_headline = subject
            im_bullets = build_im_bullets(why_it_matters, required_action, due_note)

            items.append(
                ProcurementItem(
                    source_section=source_section,
                    category=category,
                    priority=priority,
                    status=normalize_text(raw["status"]),
                    subject=subject,
                    group=group,
                    pic=normalize_text(raw["pic"]),
                    department=normalize_text(raw["department"]),
                    reference_label=reference_label,
                    reference_url=reference_url,
                    detail_lines=detail_lines,
                    why_it_matters=why_it_matters,
                    required_action=required_action,
                    due_note=due_note,
                    im_headline=im_headline,
                    im_bullets=im_bullets,
                )
            )
    return sorted(
        items,
        key=lambda item: (
            SECTION_ORDER.index(item.category) if item.category in SECTION_ORDER else 99,
            PRIORITY_ORDER.get(item.priority, 99),
            STATUS_ORDER.get(item.status, 99),
            item.subject,
        ),
    )


def build_doc_markdown(sheet_title: str, sheet_url: str, items: list[ProcurementItem]) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    stats = {
        "critical": sum(1 for item in items if item.priority == "critical"),
        "high": sum(1 for item in items if item.priority == "high"),
        "normal": sum(1 for item in items if item.priority == "normal"),
        "new": sum(1 for item in items if item.status == "New"),
        "reminder": sum(1 for item in items if item.status == "Reminder"),
    }

    lines = [
        f"# Procurement Summary [{today}]",
        "",
        "## Report Snapshot",
        "",
        f"- **Source Sheet:** [{sheet_title}]({sheet_url})",
        f"- **Generated On:** {today}",
        f"- **Critical Items:** {stats['critical']}",
        f"- **High Priority Items:** {stats['high']}",
        f"- **New Items:** {stats['new']} | **Reminders:** {stats['reminder']}",
        "",
        "## Need Action Today",
        "",
    ]

    action_items = [item for item in items if item.priority in {"critical", "high"} and item.category != "competition"][:8]
    if action_items:
        for item in action_items:
            due_text = f" | **When:** {item.due_note}" if item.due_note else ""
            lines.append(f"- **{item.subject}**: {item.required_action}{due_text}")
    else:
        lines.append("- No urgent operational actions identified.")
    lines.append("")

    for category in SECTION_ORDER:
        category_items = [item for item in items if item.category == category]
        if not category_items:
            continue
        lines.append(f"## {SECTION_LABELS[category]}")
        lines.append("")

        if category == "competition":
            for item in category_items:
                if item.reference_url:
                    label = item.reference_label if item.reference_label != "Direct reference" else item.subject
                    lines.append(f"- [{label}]({item.reference_url})")
            lines.append("")
            continue

        for item in category_items:
            status_badge = "`NEW`" if item.status == "New" else "`REMINDER`"
            priority_badge = item.priority.upper()
            lines.extend(
                [
                    f"### {status_badge} {item.subject}",
                    "",
                    f"- **Priority:** {priority_badge}",
                    f"- **Owner:** {item.pic or 'NA'} | **Department:** {item.department or 'NA'} | **Group:** {item.group or 'NA'}",
                    f"- **Why It Matters:** {item.why_it_matters}",
                    f"- **Required Action:** {item.required_action}",
                ]
            )
            if item.due_note:
                lines.append(f"- **Timeline:** {item.due_note}")
            if item.reference_url:
                lines.append(f"- **Reference:** [{item.reference_label}]({item.reference_url})")
            elif item.reference_label and item.reference_label != "Direct reference":
                lines.append(f"- **Reference:** {item.reference_label}")

            detail_lines = item.detail_lines[:4]
            if detail_lines:
                lines.append("- **Key Notes:**")
                for detail in detail_lines:
                    lines.append(f"  - {detail}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_highlights(items: list[ProcurementItem]) -> dict[str, Any]:
    payload = {
        "stats": {
            "critical": sum(1 for item in items if item.priority == "critical"),
            "high": sum(1 for item in items if item.priority == "high"),
            "new": sum(1 for item in items if item.status == "New"),
            "reminder": sum(1 for item in items if item.status == "Reminder"),
        },
        "urgent": [],
        "inventory_pricing": [],
        "promotion": [],
        "competition_urls": [item.reference_url for item in items if item.category == "competition" and item.reference_url],
    }

    for item in items:
        entry = {
            "headline": item.im_headline,
            "bullets": item.im_bullets,
            "deadline": item.due_note,
            "url": item.reference_url,
        }
        if item.category == "urgent" and item.priority in {"critical", "high"} and len(payload["urgent"]) < 5:
            payload["urgent"].append(entry)
        elif item.category == "inventory_pricing" and item.priority in {"critical", "high"} and len(payload["inventory_pricing"]) < 5:
            payload["inventory_pricing"].append(entry)
        elif item.category == "promotion" and len(payload["promotion"]) < 3:
            payload["promotion"].append(entry)
    return payload


def write_artifacts(sheet_raw: dict[str, Any], sections: dict[str, list[dict[str, Any]]], items: list[ProcurementItem], report_markdown: str, highlights: dict[str, Any]) -> None:
    (BASE_DIR / "pur_sheet_raw.json").write_text(json.dumps(sheet_raw, indent=2, ensure_ascii=False), encoding="utf-8")
    (BASE_DIR / "pur_sections.json").write_text(json.dumps(sections, indent=2, ensure_ascii=False), encoding="utf-8")
    (BASE_DIR / "pur_items.json").write_text(json.dumps([asdict(item) for item in items], indent=2, ensure_ascii=False), encoding="utf-8")
    (BASE_DIR / "pur_report.md").write_text(report_markdown, encoding="utf-8")
    (BASE_DIR / "pur_highlights.json").write_text(json.dumps(highlights, indent=2, ensure_ascii=False), encoding="utf-8")
