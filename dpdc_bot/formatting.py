"""Telegram message construction.

Kept separate from the API client so message wording can change without
touching network code, and so it can be tested with no network at all.

Nothing here emits the account holder's name or mobile number: Actions logs on
a public repo are world-readable, and so is anything forwarded from a chat.
"""

from datetime import datetime, timezone, timedelta

LOW_BALANCE_THRESHOLD = 100.0

# Asia/Dhaka is a fixed +06:00 with no DST, so a fixed offset is safe and needs
# no tzdata on the runner.
DHAKA_TZ = timezone(timedelta(hours=6))


def _now_dhaka():
    return datetime.now(timezone.utc).astimezone(DHAKA_TZ)

HELP = (
    "<b>DPDC Balance Bot</b>\n\n"
    "Sends your prepaid balance every morning at 9:00 AM (Dhaka).\n\n"
    "<b>Commands</b>\n"
    "/set 26178024 - subscribe with your customer number\n"
    "/balance - check now\n"
    "/stop - unsubscribe\n\n"
    "You can also just send your customer number.\n"
    "Unofficial bot, not affiliated with DPDC."
)


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_balance(data, previous=None, now=None):
    """Build the balance message. Deliberately omits name and mobile number."""
    balance = _as_float(data.get("balanceRemaining"))
    stamp = (now or _now_dhaka()).strftime("%d %b %Y, %I:%M %p")

    lines = [
        "<b>DPDC Balance</b>",
        f"Account : <code>{data.get('accountId')}</code>",
        f"Type    : {data.get('accountType')}",
        f"Balance : <b>Tk {balance:,.2f}</b>",
        f"Status  : {data.get('connectionStatus')}",
        f"Checked : {stamp} (Dhaka)",
    ]

    if previous is not None:
        prev = _as_float(previous, default=None)
        if prev is not None:
            delta = balance - prev
            if delta > 0.005:
                # Prepaid balance only rises on a recharge.
                lines.append(f"Recharge: +Tk {delta:,.2f} since last check")
            elif delta < -0.005:
                lines.append(f"Used    : Tk {-delta:,.2f} since last check")

    if balance < LOW_BALANCE_THRESHOLD:
        lines.append("")
        lines.append(f"Balance is below Tk {LOW_BALANCE_THRESHOLD:,.0f} - recharge soon.")

    return "\n".join(lines)
