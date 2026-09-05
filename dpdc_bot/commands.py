"""Command handling: text in, reply text out.

Deliberately free of network setup and state persistence so it can be unit
tested against a plain dict. The only I/O is the DPDC lookup used to validate a
customer number before it is stored.

    /start, /help   help text
    /set <number>   subscribe (validated against DPDC before saving)
    /balance        check right now
    /stop           unsubscribe
"""

import re

from . import dpdc
from .formatting import HELP, format_balance

CUSTOMER_RE = re.compile(r"^\d{6,15}$")

BAD_NUMBER = "That does not look like a customer number. Example: /set 26178024"
NOT_SUBSCRIBED = "Not subscribed yet. Send /set followed by your customer number."
UNKNOWN = "Unknown command. Send /help to see what I can do."


def _split(text):
    """Return (command, argument). Strips a trailing @botname used in groups."""
    parts = text.split(maxsplit=1)
    if not parts:
        return "", ""
    head = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return head, arg


def handle(text, chat_id, state):
    text = (text or "").strip()
    users = state.setdefault("users", {})
    key = str(chat_id)
    head, arg = _split(text)

    if head in ("/start", "/help"):
        return HELP

    if head == "/stop":
        if users.pop(key, None):
            return "Unsubscribed. Send /set again any time."
        return "You were not subscribed."

    if head == "/balance":
        entry = users.get(key)
        if not entry:
            return NOT_SUBSCRIBED
        try:
            data = dpdc.lookup(entry["customer"])
        except dpdc.DpdcError as exc:
            return f"Could not reach DPDC: {exc}"
        previous = entry.get("last_balance")
        entry["last_balance"] = data.get("balanceRemaining")
        return format_balance(data, previous)

    # /set <number>, or a bare number with no command at all.
    if head == "/set":
        number = arg
    elif CUSTOMER_RE.match(text):
        number = text
    else:
        return UNKNOWN

    if not CUSTOMER_RE.match(number):
        return BAD_NUMBER

    try:
        data = dpdc.lookup(number)
    except dpdc.DpdcError as exc:
        return f"Could not verify that number: {exc}"

    users[key] = {"customer": number, "last_balance": data.get("balanceRemaining")}
    return (
        "Subscribed. You will get this every morning at 9:00 AM.\n\n"
        + format_balance(data)
    )
