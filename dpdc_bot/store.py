"""Subscriber storage backed by a secret GitHub Gist.

The gist holds one file, state.json:

    {
      "offset": 828383793,
      "users": {
        "1223807097": {"customer": "26178024", "last_balance": "151.46"}
      }
    }

A secret gist is used instead of the repository so that subscribers' customer
numbers stay out of a public repo and out of Actions logs.
"""

import json

import requests

from . import config

FILENAME = "state.json"
TIMEOUT = 30

EMPTY = {"offset": 0, "users": {}}


def _api():
    return f"https://api.github.com/gists/{config.gist_id()}"


def _headers():
    return {
        "Authorization": f"Bearer {config.gist_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _blank():
    return json.loads(json.dumps(EMPTY))


def load():
    res = requests.get(_api(), headers=_headers(), timeout=TIMEOUT)
    res.raise_for_status()
    files = res.json().get("files", {})

    if FILENAME not in files:
        return _blank()

    entry = files[FILENAME]
    content = entry.get("content")
    if entry.get("truncated") and entry.get("raw_url"):
        content = requests.get(entry["raw_url"], timeout=TIMEOUT).text

    try:
        state = json.loads(content or "{}")
    except json.JSONDecodeError:
        return _blank()

    state.setdefault("offset", 0)
    state.setdefault("users", {})
    return state


def save(state):
    if config.dry_run():
        print(f"[dry-run] would save state: "
              f"offset={state.get('offset')}, users={len(state.get('users', {}))}")
        return

    res = requests.patch(
        _api(),
        headers=_headers(),
        json={"files": {FILENAME: {"content": json.dumps(state, indent=2)}}},
        timeout=TIMEOUT,
    )
    res.raise_for_status()
