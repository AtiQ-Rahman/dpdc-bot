"""Minimal Telegram Bot API wrapper.

Only the two calls this bot needs. The token is resolved per call rather than
at import time, so importing the module never requires secrets.
"""

import sys

import requests

from . import config

API_ROOT = "https://api.telegram.org"
TIMEOUT = 30


def _url(method):
    return f"{API_ROOT}/bot{config.telegram_bot_token()}/{method}"


def send(chat_id, text):
    """Send a message. Never raises - a failed send must not kill a broadcast."""
    if config.dry_run():
        print(f"[dry-run] would send to {chat_id}:\n{text}\n")
        return True

    try:
        res = requests.post(
            _url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT,
        )
        if not res.ok:
            # Log the status only - the body can echo message content.
            print(f"sendMessage failed for one chat: HTTP {res.status_code}",
                  file=sys.stderr)
        return res.ok
    except requests.RequestException as exc:
        print(f"sendMessage error: {type(exc).__name__}", file=sys.stderr)
        return False


def get_updates(offset=0, timeout=0):
    """Fetch pending updates. offset acknowledges everything below it."""
    res = requests.get(
        _url("getUpdates"),
        params={"offset": offset, "timeout": timeout, "allowed_updates": '["message"]'},
        timeout=timeout + TIMEOUT,
    )
    res.raise_for_status()
    body = res.json()
    if not body.get("ok"):
        raise RuntimeError("getUpdates returned ok=false")
    return body.get("result", [])


def get_me():
    """Identify the bot behind the current token. Used by the connectivity check."""
    res = requests.get(_url("getMe"), timeout=TIMEOUT)
    res.raise_for_status()
    return res.json().get("result", {})
