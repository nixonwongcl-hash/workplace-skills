import json
import sys
from datetime import datetime
from dataclasses import asdict

from procurement_notify import create_doc_in_folder, send_notification, send_section_d_webhook
from pur_workflow import build_doc_markdown, build_highlights, build_items, parse_sections, read_sheet_values, resolve_main_sheet, write_artifacts


def run_pur(sheet_url: str, send_im: bool = True, send_webhook: bool = True) -> dict:
    sheet_meta = resolve_main_sheet(sheet_url)
    sheet_raw = read_sheet_values(sheet_url, sheet_meta["sheet_id"], sheet_meta["row_count"])
    values = sheet_raw["data"]["valueRange"]["values"]
    sections = parse_sections(values)
    items = build_items(sections)
    report_markdown = build_doc_markdown(sheet_meta["spreadsheet_title"], sheet_url, items)
    highlights = build_highlights(items)
    write_artifacts(sheet_raw, sections, items, report_markdown, highlights)

    today = datetime.now().strftime("%d.%m.%Y")
    title = f"Procurement Summary [{today}]"
    doc_url = create_doc_in_folder(title, report_markdown)
    message_id = send_notification(doc_url, sheet_url, highlights) if send_im else ""
    section_d_items = [asdict(item) for item in items if item.source_section == "D"]
    webhook_status = send_section_d_webhook(section_d_items, sheet_url) if send_webhook and section_d_items else ""

    return {
        "sheet_title": sheet_meta["spreadsheet_title"],
        "sheet_id": sheet_meta["sheet_id"],
        "doc_url": doc_url,
        "message_id": message_id,
        "section_d_webhook": webhook_status,
        "items": len(items),
        "critical_items": highlights["stats"]["critical"],
        "high_priority_items": highlights["stats"]["high"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python execute_pur.py <sheet_url> [--doc-only] [--no-webhook]")
        sys.exit(1)

    sheet_url = sys.argv[1]
    send_im = "--doc-only" not in sys.argv[2:]
    send_webhook = "--no-webhook" not in sys.argv[2:]
    result = run_pur(sheet_url, send_im=send_im, send_webhook=send_webhook)
    print(json.dumps(result, indent=2, ensure_ascii=False))
