#!/usr/bin/env python3
"""Send a quick status message to the openPCbot Telegram chat.

Reads TELEGRAM_BOT_TOKEN + ALLOWED_CHAT_ID from ~/projetos/openpcbot/.env (kept
out of this repo — no secret is hardcoded here). Usage:

    python3 tools/notify.py "mensagem"
    echo "mensagem" | python3 tools/notify.py
"""
import json, os, sys, urllib.request, urllib.error

ENV = os.path.expanduser("~/projetos/openpcbot/.env")

def _load_env(path):
    tok = chat = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tok = line.split("=", 1)[1].strip()
            elif line.startswith("ALLOWED_CHAT_ID="):
                chat = line.split("=", 1)[1].strip()
    if not tok or not chat:
        raise SystemExit("missing TELEGRAM_BOT_TOKEN/ALLOWED_CHAT_ID in " + path)
    return tok, chat

def notify(text):
    tok, chat = _load_env(ENV)
    payload = json.dumps({"chat_id": chat, "text": text, "parse_mode": "Markdown",
                          "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("ok", False)

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]).strip() or sys.stdin.read().strip()
    if not msg:
        raise SystemExit("nada para enviar")
    print("ok" if notify(msg) else "falhou")
