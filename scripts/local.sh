#!/usr/bin/env bash
# Run any entrypoint locally with .env loaded.
#
#   scripts/local.sh check 26178024   # read-only: no sends, no writes
#   scripts/local.sh poll             # consumes the update queue, sends replies
#   scripts/local.sh broadcast        # messages every subscriber
#
# Prefix with DPDC_DRY_RUN=1 to print messages instead of delivering them:
#   DPDC_DRY_RUN=1 scripts/local.sh broadcast
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a; . ./.env; set +a
else
  echo "no .env found - copy .env.example to .env first" >&2
  exit 1
fi

target="${1:-check}"; shift || true
exec python -m "dpdc_bot.${target}" "$@"
