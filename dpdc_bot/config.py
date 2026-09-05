"""Runtime configuration, read from the environment.

Values are resolved lazily rather than at import time so that modules can be
imported (and tested) without a full set of secrets present.
"""

import os


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing."""


def _require(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} is not set. Export it, or put it in a .env file and run "
            f"through scripts/local.sh - see .env.example."
        )
    return value


def telegram_bot_token():
    return _require("TELEGRAM_BOT_TOKEN")


def gist_id():
    return _require("GIST_ID")


def gist_token():
    return _require("GIST_TOKEN")


def dpdc_client_secret():
    """DPDC's API credential. Not issued to this project - keep it out of source."""
    return _require("DPDC_CLIENT_SECRET")


def dpdc_client_id():
    return os.environ.get("DPDC_CLIENT_ID", "").strip() or "auth-ui"


def dry_run():
    """When true, no Telegram message is actually delivered and no state saved."""
    return os.environ.get("DPDC_DRY_RUN", "").strip().lower() in ("1", "true", "yes")


def check(*names):
    """Validate several variables up front so failures are loud and early."""
    missing = [n for n in names if not os.environ.get(n, "").strip()]
    if missing:
        raise ConfigError(f"missing environment variable(s): {', '.join(missing)}")
