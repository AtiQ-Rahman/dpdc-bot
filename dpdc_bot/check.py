#!/usr/bin/env python3
"""Read-only health check for local testing.

Verifies every external dependency without sending a single Telegram message,
without consuming the Telegram update queue, and without writing to the Gist.

    python -m dpdc_bot.check                 # check config, Telegram, Gist
    python -m dpdc_bot.check 26178024        # also do a live DPDC lookup
"""

import sys

import requests

from . import config, dpdc, store, telegram
from .formatting import format_balance

OK = "  ok  "
BAD = " FAIL "


def _line(status, label, detail=""):
    print(f"[{status}] {label}" + (f" - {detail}" if detail else ""))


def check_config():
    try:
        config.check("TELEGRAM_BOT_TOKEN", "GIST_ID", "GIST_TOKEN", "DPDC_CLIENT_SECRET")
    except config.ConfigError as exc:
        _line(BAD, "config", str(exc))
        return False
    _line(OK, "config", "all four secrets present")
    return True


def check_telegram():
    try:
        me = telegram.get_me()
    except (requests.RequestException, RuntimeError) as exc:
        _line(BAD, "telegram", f"{type(exc).__name__}: {exc}")
        return False
    _line(OK, "telegram", f"@{me.get('username')} (id {me.get('id')})")
    return True


def check_gist():
    try:
        state = store.load()
    except requests.RequestException as exc:
        _line(BAD, "gist", f"{type(exc).__name__}: {exc}")
        return False
    _line(OK, "gist",
          f"offset={state.get('offset')}, {len(state.get('users', {}))} subscriber(s)")
    return True


def check_dpdc(customer_number):
    try:
        data = dpdc.lookup(customer_number)
    except dpdc.DpdcError as exc:
        _line(BAD, "dpdc", str(exc))
        return False
    _line(OK, "dpdc", f"account {data.get('accountId')}")
    print()
    print(format_balance(data))
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    results = [check_config()]
    if results[0]:
        results.append(check_telegram())
        results.append(check_gist())
    if argv:
        results.append(check_dpdc(argv[0]))
    else:
        _line("skip", "dpdc", "pass a customer number to test the lookup")

    print()
    if all(results):
        print("all checks passed")
        return 0
    print("some checks failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
