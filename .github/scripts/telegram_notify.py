#!/usr/bin/env python3
"""
Telegram Notifier — professional, spam-free notifications for the NasTech
Update Pipeline. Sends concise status messages (new commits, stage passes,
failures, approvals). Never spams: only meaningful lifecycle events.

Usage:
    telegram_notify.py --token $TELEGRAM_BOT_TOKEN --chat $TELEGRAM_CHAT_ID \
        --event stage --title "Stage 4 passed" --body "verify -> semi-stage" \
        [--level success|info|error] [--file summary.md]

Events: new-commit | stage-success | stage-failure | pipeline-success |
        pipeline-failure | approval | incoming-report | manifest-missing
"""

import argparse
import requests


def build_text(event, title, body, level):
    icons = {
        "success": "✅", "info": "🔔", "error": "❌",
        "warn": "⚠️", "approved": "👍",
    }
    icon = icons.get(level, "🔔")
    header = "🤖 NasTech Update Bot"
    return f"{header}\n{icon} *{title}*\n\n{body}"


def send_message(token, chat_id, text, file_path=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Telegram send failed: {r.status_code} {r.text[:300]}")

    if file_path and os.path.exists(file_path):
        doc_url = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(file_path, "rb") as fh:
            r2 = requests.post(doc_url, data={"chat_id": chat_id}, files={"document": fh}, timeout=60)
        if r2.status_code != 200:
            raise SystemExit(f"Telegram doc send failed: {r2.status_code} {r2.text[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--chat", required=True)
    ap.add_argument("--event", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--level", default="info", choices=["success", "info", "error", "warn", "approved"])
    ap.add_argument("--file", default=None, help="optional file to attach (report/summary)")
    args = ap.parse_args()

    global os
    import os

    text = build_text(args.event, args.title, args.body, args.level)
    send_message(args.token, args.chat, text, args.file)
    print("Telegram notification sent.")


if __name__ == "__main__":
    main()
