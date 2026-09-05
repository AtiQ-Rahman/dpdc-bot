"""Command routing, with the DPDC lookup stubbed out."""

import pytest

from dpdc_bot import commands, dpdc

ACCOUNT = {
    "accountId": "26178024",
    "accountType": "Prepaid",
    "balanceRemaining": "151.46",
    "connectionStatus": "Active",
}


@pytest.fixture
def state():
    return {"offset": 0, "users": {}}


@pytest.fixture
def ok_lookup(monkeypatch):
    monkeypatch.setattr(commands.dpdc, "lookup", lambda number: ACCOUNT)


@pytest.fixture
def failing_lookup(monkeypatch):
    def boom(number):
        raise dpdc.DpdcError("no account found for that customer number")
    monkeypatch.setattr(commands.dpdc, "lookup", boom)


def test_start_returns_help(state):
    assert "DPDC Balance Bot" in commands.handle("/start", 1, state)


def test_command_with_botname_suffix(state):
    assert "DPDC Balance Bot" in commands.handle("/help@dpdc_bot", 1, state)


def test_set_subscribes(state, ok_lookup):
    reply = commands.handle("/set 26178024", 555, state)
    assert "Subscribed" in reply
    assert state["users"]["555"]["customer"] == "26178024"


def test_bare_number_subscribes(state, ok_lookup):
    commands.handle("26178024", 555, state)
    assert state["users"]["555"]["customer"] == "26178024"


def test_set_rejects_non_numeric(state):
    assert commands.handle("/set abc", 555, state) == commands.BAD_NUMBER
    assert state["users"] == {}


def test_set_not_saved_when_dpdc_rejects(state, failing_lookup):
    reply = commands.handle("/set 26178024", 555, state)
    assert "Could not verify" in reply
    assert state["users"] == {}


def test_balance_requires_subscription(state):
    assert commands.handle("/balance", 555, state) == commands.NOT_SUBSCRIBED


def test_balance_updates_last_seen(state, ok_lookup):
    state["users"]["555"] = {"customer": "26178024", "last_balance": "100.00"}
    reply = commands.handle("/balance", 555, state)
    assert "Recharge" in reply and "51.46" in reply
    assert state["users"]["555"]["last_balance"] == "151.46"


def test_stop_unsubscribes(state):
    state["users"]["555"] = {"customer": "26178024"}
    assert "Unsubscribed" in commands.handle("/stop", 555, state)
    assert state["users"] == {}


def test_stop_when_not_subscribed(state):
    assert "not subscribed" in commands.handle("/stop", 555, state).lower()


def test_unknown_text(state):
    assert commands.handle("hello there", 555, state) == commands.UNKNOWN


def test_empty_text(state):
    assert commands.handle("", 555, state) == commands.UNKNOWN


def test_none_text(state):
    assert commands.handle(None, 555, state) == commands.UNKNOWN
