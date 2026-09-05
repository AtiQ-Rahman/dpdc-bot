"""DPDC quick-pay API client.

The public frontend mints an anonymous bearer token by POSTing an empty body to
/auth/login/generate-bearer with a clientId/clientSecret pair that ships inside
its JS bundle. Tokens expire in ~15 minutes, so we mint a fresh one per run.

This module talks to DPDC and nothing else - message formatting lives in
:mod:`dpdc_bot.formatting`.
"""

import requests

from . import config

BASE = "https://amiapp.dpdc.org.bd"
AUTH_URL = f"{BASE}/auth/login/generate-bearer"
API_URL = f"{BASE}/usage/usage-service"

TENANT = "DPDC"

TIMEOUT = 30

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
    "tenantCode": TENANT,
    "Origin": BASE,
    "Referer": f"{BASE}/quick-pay",
    "User-Agent": UA,
}

BALANCE_FIELDS = (
    "accountId customerName customerClass accountType "
    "balanceRemaining connectionStatus minRecharge"
)


class DpdcError(Exception):
    """Raised when DPDC returns something we can't use."""


def new_session():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    return session


def get_token(session):
    try:
        res = session.post(
            AUTH_URL,
            json={},
            timeout=TIMEOUT,
            headers={
                "clientId": config.dpdc_client_id(),
                "clientSecret": config.dpdc_client_secret(),
            },
        )
    except requests.RequestException as exc:
        raise DpdcError(f"auth request failed: {type(exc).__name__}")

    if res.status_code not in (200, 201):
        raise DpdcError(f"auth returned HTTP {res.status_code}")

    try:
        body = res.json()
    except ValueError:
        raise DpdcError("auth response was not JSON (clientSecret may have rotated)")

    token = body.get("access_token") or body.get("accessToken") or body.get("token")
    if not token:
        raise DpdcError("no access_token in auth response")
    return token


def fetch_balance(session, token, customer_number):
    query = (
        'query{ postBalanceDetails(input:{customerNumber:"%s",tenantCode:"%s"})'
        "{ %s }}" % (customer_number, TENANT, BALANCE_FIELDS)
    )
    try:
        res = session.post(
            API_URL,
            json={"query": query},
            timeout=TIMEOUT,
            headers={"Authorization": f"Bearer {token}", "accessToken": token},
        )
    except requests.RequestException as exc:
        raise DpdcError(f"usage-service request failed: {type(exc).__name__}")

    if res.status_code != 200:
        raise DpdcError(f"usage-service returned HTTP {res.status_code}")

    try:
        body = res.json()
    except ValueError:
        raise DpdcError("usage-service response was not JSON")

    if body.get("errors"):
        raise DpdcError(str(body["errors"])[:200])

    data = (body.get("data") or {}).get("postBalanceDetails")
    if not data:
        raise DpdcError("no account found for that customer number")
    return data


def lookup(customer_number):
    """One-shot convenience helper: mint a token and fetch one account."""
    session = new_session()
    return fetch_balance(session, get_token(session), customer_number)
