"""Regression tests for the blank-state copy."""

from dpdc_bot import store


def test_blank_is_not_shared():
    a = store._blank()
    a["users"]["1"] = {"customer": "26178024"}
    b = store._blank()
    assert b["users"] == {}
    assert store.EMPTY["users"] == {}
