"""Formatting is pure, so it is tested with no network and no secrets."""

from dpdc_bot.formatting import format_balance

SAMPLE = {
    "accountId": "26178024",
    "customerName": "Someone Private",
    "accountType": "Prepaid",
    "balanceRemaining": "151.46",
    "connectionStatus": "Active",
}


def test_includes_account_and_balance():
    out = format_balance(SAMPLE)
    assert "26178024" in out
    assert "Tk 151.46" in out


def test_never_leaks_name():
    assert "Someone Private" not in format_balance(SAMPLE)


def test_recharge_detected_when_balance_rises():
    out = format_balance(SAMPLE, previous="100.00")  # 100 -> 151.46
    assert "Recharge" in out
    assert "51.46" in out


def test_usage_shown_when_balance_falls():
    out = format_balance(SAMPLE, previous="200.00")  # 200 -> 151.46
    assert "Used" in out
    assert "48.54" in out


def test_no_change_line_when_flat():
    out = format_balance(SAMPLE, previous="151.46")
    assert "Recharge" not in out and "Used" not in out


def test_no_delta_line_without_previous():
    out = format_balance(SAMPLE)
    assert "Recharge" not in out and "Used" not in out


def test_garbage_previous_is_ignored():
    out = format_balance(SAMPLE, previous="not-a-number")
    assert "Recharge" not in out and "Used" not in out


def test_low_balance_warning():
    low = dict(SAMPLE, balanceRemaining="42.00")
    assert "recharge soon" in format_balance(low)
    assert "recharge soon" not in format_balance(SAMPLE)


def test_missing_balance_treated_as_zero():
    out = format_balance({"accountId": "1", "balanceRemaining": None})
    assert "Tk 0.00" in out


def test_timestamp_is_shown():
    from datetime import datetime
    from dpdc_bot.formatting import DHAKA_TZ
    fixed = datetime(2026, 9, 5, 22, 36, tzinfo=DHAKA_TZ)
    out = format_balance(SAMPLE, now=fixed)
    assert "05 Sep 2026, 10:36 PM (Dhaka)" in out
