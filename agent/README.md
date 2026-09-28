# EdgeLog Trader Agent

**Strategy Trader ST0** -- the local execution foundation. This is
infrastructure only: it authenticates to TopstepX, discovers your
accounts, resolves the active MNQ contract, and observes live market
data. **It does not place, modify, or cancel orders, and it never will
autonomously.** Order placement is explicitly out of scope until ST1.

## Why this runs on your machine, not the EdgeLog server

EdgeLog's cloud server (the one at edgelog.trade / d.edgelog.trade) is a
journal, configuration, and analytics tool. It is **not** part of the
trading path:

```
EdgeLog Cloud (DigitalOcean)          Your Windows PC              TopstepX / ProjectX
------------------------------        ------------------------      --------------------
journal, configuration,        <----  EdgeLog Trader Agent   ----->  execution provider
analytics, strategy results,          (this project)
read-only status                      - TopstepX auth
                                       - live market data
                                       - account/contract discovery
                                       - (later) strategy engine
                                       - (later) risk engine
                                       - (later) order manager
                                       - all trading activity
                                         originates HERE
```

Concretely:

- Your TopstepX API key lives only in a local `.env` file on your machine
  (see below). It is never sent to, logged by, or stored in EdgeLog
  cloud, and this repo's `.gitignore` is configured so it can never be
  committed by accident.
- This agent talks directly to `api.topstepx.com` / `rtc.topstepx.com`.
  EdgeLog cloud has no code path that can originate a TopstepX order --
  there is nothing in `backend/` that talks to TopstepX at all as of
  ST0.
- Later Strategy Trader issues (ST1+) add order placement, but that logic
  will live in this same local agent, gated behind explicit kill controls
  and a risk engine. The trading decision and the order request will
  always originate on your device.

If you ever see EdgeLog cloud asking you to paste in a TopstepX API key,
that is not how this is designed to work -- don't do it.

## Prerequisites

- Windows 10/11
- Python 3.11+ ([python.org](https://www.python.org/downloads/windows/))
- A TopstepX account with API access enabled and an API key generated
  from the TopstepX platform's own API settings (Settings -> API in the
  TopstepX web app). Topstep's own help article: search "TopstepX API
  Access" in their help center if you don't see this option.

## Setup (Windows)

Open PowerShell in this `agent/` directory:

```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
notepad .env
```

Fill in `.env`:

- `TOPSTEPX_USERNAME` -- your TopstepX login username.
- `TOPSTEPX_API_KEY` -- your API key. Treat it like a password. Never
  paste it into a chat, a GitHub issue/PR, or anywhere in EdgeLog cloud.
- Leave `TOPSTEPX_PRACTICE_ACCOUNT_ID` blank for the first run.

## First run: find your Practice account ID

```powershell
python -m trader_agent status
```

This authenticates, lists your accounts (in the structured log output --
see `agent/logs/agent-<date>.log`), auto-detects which one looks like
your Practice account, resolves the active MNQ contract, and prints a
one-line status, then exits. Check the log for the
`agent.practice_account_selected` (or `agent.no_practice_account_found`)
event and confirm the account ID is actually your Practice account.

**Important:** the auto-detection is a best-effort heuristic (see the
comment at the top of `trader_agent/providers/topstepx/client.py`) --
TopstepX's exact account-search response fields weren't independently
verifiable while building this without live API access. Once you've
confirmed the correct account ID from the log, set it explicitly:

```
TOPSTEPX_PRACTICE_ACCOUNT_ID=<the id you confirmed>
```

From then on, the agent uses that pinned ID instead of the heuristic, so
there is no ambiguity about which account it's looking at.

## Running the agent

```powershell
python -m trader_agent start
```

Runs until you press Ctrl+C, printing a status line every 5 seconds:

```
connection=connected execution_capable=True account=123456 contract=CON.F.US.MNQ.Z25 last_price=21005.5
```

- `connection` -- one of `disconnected`, `connecting`, `connected`,
  `reconnecting`, `stale`.
- `execution_capable` -- **always relevant for future issues, not this
  one** -- ST0 never acts on it. It's `False` whenever the connection
  isn't authenticated+connected+fresh, which is exactly the gate ST1's
  order placement will read before ever sending an order.
- `stale` shows up if market data stops arriving for more than
  `TOPSTEPX_STALE_AFTER_SECONDS` (default 15s) -- check your network and
  that the market is open.

## Logs

Structured (JSON-line) logs go to `agent/logs/agent-<date>.log` and to
the console. Every log line passes through a redaction filter that
strips your API key (and, once authenticated, your session token) from
the message -- see `trader_agent/logging_setup.py` and its tests. If you
ever find a credential in a log file, that's a bug: open an issue.

## Running the tests

```powershell
pip install -r requirements.txt
pytest
```

All 54 tests run against fakes/mocks -- no network access and no
TopstepX credentials required. The one piece that is *not* covered by
this suite is `SignalRTransport` (`trader_agent/providers/topstepx/realtime.py`),
the thin adapter onto the real `signalrcore` SignalR client library --
everything that actually has logic in it (subscription bookkeeping,
reconnect handling, health/staleness tracking) is factored out into
`RealtimeHub`, which is fully tested against a fake transport. Verifying
`SignalRTransport` itself requires a real connection, which is why `python
-m trader_agent status` against your own Practice account is part of the
acceptance pass for this issue, not just the test suite.

## What's verified vs. inferred

This agent was built without live network access to
`gateway.docs.projectx.com` (the primary ProjectX API docs). The
following were confirmed from multiple independent public sources
(cross-referenced third-party SDKs and documentation excerpts):

- `POST https://api.topstepx.com/api/Auth/loginKey` with
  `{"userName", "apiKey"}`, returning `{"token", "success", "errorCode",
  "errorMessage"}`.
- `POST /api/Account/search`, `POST /api/Contract/search` exist as POST
  endpoints under the same base URL.
- Contract objects have `id` (format `CON.F.US.<SYMBOL>.<expiry>`),
  `name`, `description`, `tickSize`, `tickValue`, `activeContract`,
  `symbolId`.
- SignalR hubs at `{rtc_base_url}/hubs/user` and `{rtc_base_url}/hubs/market`,
  authenticated via `?access_token=<jwt>` in the connection URL.
- User hub subscribe methods `SubscribeAccounts`, `SubscribeOrders`,
  `SubscribePositions`, `SubscribeTrades`; market hub subscribe methods
  `SubscribeContractQuotes`, `SubscribeContractTrades`.
- User hub events `GatewayUserAccount`, `GatewayUserOrder`,
  `GatewayUserPosition`, `GatewayUserTrade`; market hub events
  `GatewayQuote`, `GatewayTrade` (and `GatewayDepth`, not yet wired up).

**Not independently confirmed** -- verify these against your own account
on first run:

- The exact field names TopstepX uses to mark an account as Practice vs.
  other account types (see `TOPSTEPX_PRACTICE_ACCOUNT_ID` above).
- The exact shape of the SignalR user-hub event payloads (order/position
  fields). ST0 only logs that an update was received; parsing individual
  fields out of it is ST4's job (automatic journaling), not this issue's.

If anything above turns out to not match TopstepX's real behavior, that's
expected -- report it and it gets fixed before ST1 builds order placement
on top of this foundation.

## Not yet built (intentionally out of scope for ST0)

- Running as an actual Windows Service (this is a foreground console
  process for now).
- Order placement/cancellation, kill controls, risk engine (ST1+).
- Any code path that lets EdgeLog cloud influence trading (by design,
  permanently -- not just "not yet").
- Reading/writing EdgeLog cloud data at all. This agent is fully
  standalone; a read-only status sync to EdgeLog cloud is a reasonable
  future addition but wasn't required by ST0's acceptance criteria and
  would mean touching `backend/`, which this issue deliberately does not.
