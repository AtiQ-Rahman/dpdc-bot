# DPDC Balance Bot

A Telegram bot that sends DPDC prepaid meter balances every morning at 9:00 AM
(Asia/Dhaka). Runs entirely on GitHub Actions — no server, no cost.

Unofficial. Not affiliated with or endorsed by Dhaka Power Distribution Company.

## Layout

```
.github/workflows/
  poll.yml            every 20 min - handles commands
  daily.yml           once a day  - sends everyone their balance
dpdc_bot/
  config.py           environment variables, resolved lazily
  dpdc.py             DPDC API client - network only
  formatting.py       message text - pure, no network
  commands.py         command routing - /set, /balance, /stop
  telegram.py         Bot API wrapper - sendMessage, getUpdates, getMe
  store.py            subscriber state in a secret Gist
  poll.py             entrypoint: python -m dpdc_bot.poll
  broadcast.py        entrypoint: python -m dpdc_bot.broadcast
  check.py            entrypoint: python -m dpdc_bot.check  (read-only)
scripts/local.sh      run any entrypoint with .env loaded
stats/history.csv     daily subscriber/sent/failed counts (no PII)
tests/                pytest - no network, no secrets needed
```

The split exists so the two parts that hold the logic worth testing —
`formatting.py` and `commands.py` — have no network dependency at all, and so
`dpdc.py` can be swapped or updated without touching message wording.

## How it works

A bearer token is minted by POSTing an empty body to
`/auth/login/generate-bearer` with a `clientId` / `clientSecret` pair. Tokens
expire in about 15 minutes, so a fresh one is minted on every run.

The secret is **not** hardcoded here. It is read from `DPDC_CLIENT_SECRET`,
because it is not a credential this project was issued and it is not published
anywhere by DPDC — it does not appear in any of their frontend bundles. Do not
paste it into source, an issue, or a screenshot.

## Setup

### 1. Create the bot

Message [@BotFather](https://t.me/BotFather), send `/newbot`, and keep the token.

### 2. Create the state Gist

Go to <https://gist.github.com>, create a **secret** gist with one file named
`state.json` containing:

```json
{ "offset": 0, "users": {} }
```

Save it and copy the ID from the URL (`gist.github.com/<user>/<THIS_PART>`).

### 3. Create a token for the Gist

Settings → Developer settings → Personal access tokens → **Tokens (classic)** →
Generate new token, with only the **`gist`** scope checked.

A fine-grained token will not work here — the Gist API only accepts classic
tokens.

### 4. Add repository secrets

Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `GIST_ID` | The secret gist's ID |
| `GIST_TOKEN` | The classic PAT with `gist` scope |
| `DPDC_CLIENT_SECRET` | The DPDC API client secret |

### 5. Enable the workflows

Push to the default branch, open the **Actions** tab, and enable workflows if
prompted. Run **Poll commands** manually once to confirm it works.

Then message your bot `/set 26178024` and wait up to 10 minutes for the reply.

## Running locally

```bash
pip install -r requirements-dev.txt
cp .env.example .env      # then fill in the three values
```

Start with the health check. It is read-only: it sends no message, does not
consume the Telegram update queue, and does not write to the Gist.

```bash
scripts/local.sh check              # config, Telegram, Gist
scripts/local.sh check 26178024     # the above, plus a live DPDC lookup
```

Then the real entrypoints. `DPDC_DRY_RUN=1` prints every message instead of
delivering it and skips the Gist write, which is the safe way to try either one:

```bash
DPDC_DRY_RUN=1 scripts/local.sh poll
DPDC_DRY_RUN=1 scripts/local.sh broadcast

scripts/local.sh poll         # for real: replies to users, advances the offset
scripts/local.sh broadcast    # for real: messages every subscriber
```

Tests need no secrets and touch no network:

```bash
python -m pytest tests/ -q
```

## Daily stats

Each daily run appends one row to `stats/history.csv` (date, subscribers, sent,
failed) and the workflow commits it. Only counts are recorded - never a customer
number or chat id, so it is safe in a public repo. This commit also keeps the
repository active, which stops GitHub from auto-disabling the schedule (see
below).

## Things that will bite you

**Workflows must live in `.github/workflows/`.** A workflow file anywhere else
is inert — GitHub will not report an error, it simply never runs.

**Cron is UTC, and it is late.** `03:00` UTC is `09:00` in Dhaka. GitHub
frequently delays scheduled runs by 5–30 minutes under load, so `daily.yml`
fires at 02:45 UTC and sleeps until 03:00. If GitHub is very late the sleep is
skipped and the message simply goes out late.

**Replies are not instant.** Registration is handled by a 20-minute poll, not a
webhook. A user who sends `/set` may wait up to 20 minutes. Making this instant
requires a real always-on host.

**Only one thing may touch the Gist at a time.** Both workflows share
`concurrency: dpdc-state` for this reason. Running `poll` locally while the
Actions run is in flight can still lose an update — the Gist has no
compare-and-swap.

**Workflows auto-disable after 60 days of no commits.** GitHub disables
scheduled workflows if a repo goes 60 days without a commit. The daily stats
commit prevents this on its own - as long as the daily job runs, the repo never
goes idle. If the daily job itself stops, re-enable the workflows from the
Actions tab.

**Keep the repository public.** Public repos get unlimited Actions minutes;
private repos get 2,000/month, and polling every 20 minutes needs roughly 2,150.
Subscriber data lives in the secret Gist, not in the repo, precisely so the repo
can stay public.

**The client secret can rotate.** DPDC may change it without warning. When that
happens the bot reports a clear error instead of failing silently; update the
`DPDC_CLIENT_SECRET` secret and your local `.env`. Never put the new value back
into a source file.

**This is a personal-use tool.** It authenticates with a credential DPDC did not
issue for this purpose. Fine for reading your own meter; think carefully before
inviting others to subscribe or making the repository public.

**Log hygiene.** Actions logs on a public repo are readable by anyone, and the
DPDC response contains the account holder's name and mobile number. Nothing here
prints those, and messages omit them too — `tests/test_formatting.py` asserts
it. Keep it that way if you extend it.

**Only prepaid accounts.** The `postBalanceDetails` query returns
`balanceRemaining`, which is a prepaid concept. Postpaid accounts return
different fields and will need a different query.

## Rate limits

One token is minted per broadcast and reused across subscribers, and there is a
1-second gap between sends. That is comfortable for tens of users. At hundreds,
add batching and back off on DPDC failures before you get blocked.
