"""
Procurement Update notification helpers.

Usage:
  python procurement_notify.py <sheet_url> <doc_url> [<highlights_json_path>]

This script reads highlights from a file when provided and sends a rich
Lark post message via the bot. It also exposes helpers for doc creation.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib import request

from pur_workflow import BOT_USER_ID, DRIVE_FOLDER_TOKEN, LARK_CLI, SECTION_D_WEBHOOK_URL


def _run_lark_cli(args):
    result = subprocess.run(
        [LARK_CLI, *args],
        capture_output=True,
        text=True,
        shell=False,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "lark-cli command failed")
    payload = json.loads(result.stdout.strip())
    if not payload.get("ok"):
        error = payload.get("error", {}).get("message", "Unknown Lark API error")
        raise RuntimeError(error)
    return payload


def build_post_content(doc_url, sheet_url, highlights=None):
    today = datetime.now().strftime("%d %b %Y")
    highlights = highlights or {}
    stats = highlights.get("stats", {})

    lines = [
        [{"tag": "text", "text": "Procurement Update Snapshot", "style": ["bold"]}],
        [
            {"tag": "text", "text": f"Critical: {stats.get('critical', 0)} | High: {stats.get('high', 0)} | New: {stats.get('new', 0)} | Reminder: {stats.get('reminder', 0)}"}
        ],
        [],
    ]

    if highlights.get("urgent"):
        lines.append([{"tag": "text", "text": "Urgent Actions", "style": ["bold"]}])
        for item in highlights["urgent"]:
            lines.append([{"tag": "text", "text": f"• {item['headline']}", "style": ["bold"]}])
            for bullet in item.get("bullets", [])[:2]:
                lines.append([{"tag": "text", "text": f"  - {bullet}"}])
            if item.get("deadline"):
                lines.append([{"tag": "text", "text": f"  - Due: {item['deadline']}"}])
            if item.get("url"):
                lines.append([{"tag": "a", "text": "  View reference", "href": item["url"]}])
        lines.append([])

    if highlights.get("inventory_pricing"):
        lines.append([{"tag": "text", "text": "Inventory and Pricing", "style": ["bold"]}])
        for item in highlights["inventory_pricing"]:
            lines.append([{"tag": "text", "text": f"• {item['headline']}", "style": ["bold"]}])
            for bullet in item.get("bullets", [])[:2]:
                lines.append([{"tag": "text", "text": f"  - {bullet}"}])
            if item.get("url"):
                lines.append([{"tag": "a", "text": "  View reference", "href": item["url"]}])
        lines.append([])

    if highlights.get("promotion"):
        lines.append([{"tag": "text", "text": "Promotions", "style": ["bold"]}])
        for item in highlights["promotion"]:
            lines.append([{"tag": "text", "text": f"• {item['headline']}", "style": ["bold"]}])
            for bullet in item.get("bullets", [])[:2]:
                lines.append([{"tag": "text", "text": f"  - {bullet}"}])
            if item.get("url"):
                lines.append([{"tag": "a", "text": "  View promo file", "href": item["url"]}])
        lines.append([])

    lines.extend(
        [
            [{"tag": "text", "text": "Full Report", "style": ["bold"]}],
            [{"tag": "a", "text": "Open detailed Procurement Summary", "href": doc_url}],
            [{"tag": "a", "text": "Open source sheet", "href": sheet_url}],
        ]
    )
    if highlights.get("competition_urls"):
        lines.append([{"tag": "text", "text": "Competition links are listed in the full report."}])

    return {
        "en_us": {
            "title": f"Procurement Intelligence Brief | {today}",
            "content": lines,
        }
    }


def send_notification(doc_url, sheet_url, highlights=None):
    content = build_post_content(doc_url, sheet_url, highlights)
    payload = _run_lark_cli(
        [
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--user-id",
            BOT_USER_ID,
            "--msg-type",
            "post",
            "--content",
            json.dumps(content, ensure_ascii=False),
        ]
    )
    message_id = payload["data"]["message_id"]
    print(f"[OK] Message sent: {message_id}")
    return message_id


def build_section_d_card(section_d_items, sheet_url):
    today = datetime.now().strftime("%d%m%Y")
    elements = [
        {
            "tag": "markdown",
            "content": f"**Summary | {today} | Promotion Activities / Awareness Campaign**\nEligible Section D items for `BCG Outlets` and `Big Outlets` only.",
        },
        {"tag": "hr"},
    ]

    for item in section_d_items:
        details = item.get("detail_lines", [])
        short_bits = []
        for detail in details:
            if detail.startswith("PROMOTION MECHANISM:") or detail.startswith("PROMOTION PERIOD:") or detail.startswith("Dear outlets"):
                short_bits.append(detail)
        if not short_bits:
            short_bits = details[:2]

        body_lines = [
            f"**Status:** {item.get('status', 'NA')}",
            f"**Group:** {item.get('group', 'NA')}",
            f"**PIC / Dept:** {item.get('pic', 'NA')} / {item.get('department', 'NA')}",
        ]
        for bit in short_bits[:3]:
            body_lines.append(f"- {bit}")
        if item.get("reference_url"):
            body_lines.append(f"[Open reference]({item['reference_url']})")

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{item['subject']}**\n" + "\n".join(body_lines),
                },
            }
        )
        elements.append({"tag": "hr"})

    elements.append(
        {
            "tag": "note",
            "elements": [
                {"tag": "lark_md", "content": f"[Open source sheet]({sheet_url})"},
            ],
        }
    )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"Summary | {today} | Section D",
                },
                "template": "blue",
            },
            "elements": elements,
        },
    }


def send_section_d_webhook(section_d_items, sheet_url, webhook_url=SECTION_D_WEBHOOK_URL):
    if not section_d_items:
        return ""
    payload = build_section_d_card(section_d_items, sheet_url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("code") not in (0, None):
        raise RuntimeError(f"Webhook send failed: {data}")
    print("[OK] Section D webhook sent")
    return data.get("msg", "ok")


def create_doc_in_folder(title, markdown_content):
    payload = _run_lark_cli(
        [
            "docs",
            "+create",
            "--as",
            "user",
            "--title",
            title,
            "--folder-token",
            DRIVE_FOLDER_TOKEN,
            "--markdown",
            markdown_content,
        ]
    )
    doc_url = payload["data"]["doc_url"]
    print(f"[OK] Doc created: {doc_url}")
    return doc_url


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python procurement_notify.py <sheet_url> <doc_url> [<highlights_json_path>]")
        sys.exit(1)

    sheet_url = sys.argv[1]
    doc_url = sys.argv[2]
    highlights = None

    if len(sys.argv) > 3:
        highlights_path = Path(sys.argv[3])
        highlights = json.loads(highlights_path.read_text(encoding="utf-8"))

    send_notification(doc_url, sheet_url, highlights)
