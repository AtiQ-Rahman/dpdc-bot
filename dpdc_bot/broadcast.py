#!/usr/bin/env python3
"""Send every subscriber their current balance. Runs once a day.

    python -m dpdc_bot.broadcast
"""

import csv
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import config, dpdc, store, telegram
from .formatting import format_balance

STATS_FILE = Path(__file__).resolve().parent.parent / "stats" / "history.csv"
STATS_HEADER = ["date", "subscribers", "sent", "failed"]


def record_stats(subscribers, sent, failed):
    """Append one row of run stats. Counts only - never any customer data."""
    if config.dry_run():
        print(f"[dry-run] would record stats: "
              f"subscribers={subscribers}, sent={sent}, failed={failed}")
        return
    date = datetime.now(timezone(timedelta(hours=6))).strftime("%Y-%m-%d")
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    new = not STATS_FILE.exists()
    with STATS_FILE.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(STATS_HEADER)
        writer.writerow([date, subscribers, sent, failed])
    print(f"recorded stats for {date}")

SEND_INTERVAL = 1  # seconds; stays well inside Telegram's 30 msg/sec limit


def main():
    try:
        config.check("TELEGRAM_BOT_TOKEN", "GIST_ID", "GIST_TOKEN", "DPDC_CLIENT_SECRET")
    except config.ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    state = store.load()
    users = state.get("users", {})

    if not users:
        print("no subscribers")
        return 0

    session = dpdc.new_session()
    try:
        token = dpdc.get_token(session)
    except dpdc.DpdcError as exc:
        print(f"could not mint token: {exc}", file=sys.stderr)
        return 1

    sent = failed = 0
    for chat_id, entry in list(users.items()):
        try:
            data = dpdc.fetch_balance(session, token, entry["customer"])
        except dpdc.DpdcError as exc:
            telegram.send(chat_id, f"Could not fetch your balance today: {exc}")
            failed += 1
            continue

        message = format_balance(data, entry.get("last_balance"))
        if telegram.send(chat_id, message):
            sent += 1
        else:
            failed += 1

        entry["last_balance"] = data.get("balanceRemaining")
        time.sleep(SEND_INTERVAL)

    store.save(state)
    record_stats(len(users), sent, failed)
    print(f"sent {sent}, failed {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
