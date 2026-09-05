#!/usr/bin/env python3
"""Poll Telegram for new commands and update the subscriber list.

Runs on a schedule, so replies arrive within one polling interval rather than
instantly.

    python -m dpdc_bot.poll
"""

import sys

from . import commands, config, store, telegram


def main():
    try:
        config.check("TELEGRAM_BOT_TOKEN", "GIST_ID", "GIST_TOKEN", "DPDC_CLIENT_SECRET")
    except config.ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    state = store.load()
    updates = telegram.get_updates(offset=state.get("offset", 0))

    if not updates:
        print("no new updates")
        return 0

    changed = False
    for update in updates:
        state["offset"] = update["update_id"] + 1
        changed = True

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private":
            continue

        try:
            reply = commands.handle(message.get("text"), chat["id"], state)
        except Exception as exc:  # one bad message must not stall the queue
            print(f"handler error: {type(exc).__name__}", file=sys.stderr)
            reply = "Something went wrong. Please try again."

        telegram.send(chat["id"], reply)

    if changed:
        store.save(state)
    print(f"processed {len(updates)} update(s), {len(state['users'])} subscriber(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
