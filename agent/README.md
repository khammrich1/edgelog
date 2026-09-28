# EdgeLog Trader Agent

**Strategy Trader ST0 + ST1.** ST0 built the local execution foundation:
authentication to TopstepX, account/contract discovery, and live market
data. ST1 adds the ability to submit and manage exactly one kind of
order -- a **manually reviewed, manually confirmed, Practice-account MNQ
limit order** -- through this same local agent. **Nothing in this
codebase places an order without an explicit human typing `CONFIRM` at a
terminal prompt first.** There is no autonomous strategy, no automatic
order authorization, and no path from EdgeLog cloud to an order -- see
"Why this runs on your machine" below and `docs/ST1_SCOPE.md`.

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
- ST1 (this version) adds order placement, but that logic lives in this
  same local agent, gated behind a manual confirmation prompt, a hard
  quantity cap, and a local kill switch -- see "Placing and managing
  orders (ST1)" below. Later issues (ST2+) add a strategy engine and risk
  engine, but the trading decision and the order request will always
  originate on your device.

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

## Placing and managing orders (ST1)

Everything below is Practice-account, limit-order-only, and requires a
human to type an exact confirmation string. There is no other way to
submit an order from this codebase.

```powershell
python -m trader_agent order
```

This starts the agent, checks that it's execution-capable (authenticated,
connected, market data fresh) and that the kill switch isn't engaged,
then walks you through:

1. Side (`buy`/`sell`)
2. Quantity -- refused if it exceeds `TOPSTEPX_MAX_ORDER_QUANTITY`
   (default 1) regardless of what you type
3. Limit price
4. A full review screen (account, contract, side, quantity, price)
5. **`Type CONFIRM to submit this order, anything else cancels:`** --
   anything other than the exact word `CONFIRM` cancels with no order sent

If the account resolved isn't flagged as your Practice account, the order
is refused before it ever reaches TopstepX -- there's no way to point this
at a live account.

```powershell
python -m trader_agent orders          # list locally tracked orders + last known status
python -m trader_agent cancel <tag>    # cancel a working order by its EdgeLog tag (from `orders`)
```

Canceling is **never** blocked by the kill switch below -- a kill switch
should make it easier, not harder, to reduce risk that's already on.

### Kill switch

```powershell
python -m trader_agent kill --reason "stepping away"   # engage -- blocks all new order submission
python -m trader_agent kill --clear                    # clear it again
```

This is a plain local JSON file (`agent/.state/trading_control.json`), not
a network call -- it works even if TopstepX or your internet connection is
down, and it persists across restarts until you explicitly clear it. It
blocks new order submission only; canceling an existing working order
still works while it's engaged.

There's also a separate, always-off `auto_trading_enabled` flag in that
same file. Nothing in ST0/ST1 can set it to `true` -- it exists now so
ST3's risk engine has one settled flag to check later, and it's forced
back to `false` on every agent start regardless of what's on disk, so a
restart can never silently resume automated trading once that exists.

### Duplicate protection and reconciliation

Every order gets a unique `edgelog-<random>` tag; submitting an order
with the exact same account/contract/side/quantity/price as one that's
still open (working, partially filled, or mid-submission) is refused --
cancel the existing one first if you meant to replace it. On every
`start`/`status`/`order`/`cancel`/`orders` invocation, the agent also
pulls your Practice account's order history from TopstepX and reconciles
fill state into its local records, so a crash or restart between
submitting an order and seeing its result doesn't lose track of it.

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

All 114 tests run against fakes/mocks -- no network access and no
TopstepX credentials required. The one piece that is *not* covered by
this suite is `SignalRTransport` (`trader_agent/providers/topstepx/realtime.py`),
the thin adapter onto the real `signalrcore` SignalR client library --
everything that actually has logic in it (subscription bookkeeping,
reconnect handling, health/staleness tracking, order safety gating,
duplicate protection, reconciliation, the kill switch) is factored out
into classes tested against fakes. Verifying `SignalRTransport` itself,
and whether a real order actually reaches TopstepX and behaves as this
code expects, requires a real Practice-account connection -- which is why
`python -m trader_agent order` against your own Practice account is part
of the acceptance pass for this issue, not just the test suite.

## What's verified vs. inferred

This agent was built without live network access to
`gateway.docs.projectx.com` (the primary ProjectX API docs) -- blocked by
this sandbox's network egress policy for the entire build. The
authoritative reference is now
[`docs/integrations/projectx/PROJECTX_API_REFERENCE.md`](../docs/integrations/projectx/PROJECTX_API_REFERENCE.md),
an EdgeLog-owned distillation of the official docs (reviewed 2026-09-28);
this code follows it, including its own explicit "Gaps / do not guess"
list. Where that reference itself doesn't confirm something, this
codebase is written defensively rather than guessing -- notably:

- **Contract resolution uses `/api/Contract/available`, not
  `/api/Contract/search`.** The reference explicitly flags the search
  endpoint's request schema as unverified; `/available`'s is fully
  documented, and filtering its full contract list client-side for the
  target symbol's active month is sufficient for ST0.
- **Quotes are attributed by subscription, not by a field in the
  payload.** The reference's documented quote fields (`symbol`,
  `symbolName`, `lastPrice`, `bestBid`, `bestAsk`, ...) don't include a
  contract ID, so `TopstepXProvider` tracks "the contract_id I last
  subscribed to" itself rather than trying to parse one out of each
  quote. This only works because ST0 subscribes to one contract at a
  time -- revisit if a later issue needs multiple simultaneous contracts.
- **Practice-account detection remains a name-based heuristic.** The
  reference's documented `/api/Account/search` fields
  (`id`/`name`/`balance`/`canTrade`/`isVisible`) don't include anything
  that distinguishes a Practice account; it only notes that *realtime*
  payloads may expose `simulated`. This is exactly why
  `TOPSTEPX_PRACTICE_ACCOUNT_ID` exists -- pin it after your first run
  rather than trusting the heuristic.
- **Exact SignalR subscribe-method and event names are still
  unconfirmed even by the new reference** -- it explicitly lists this as
  a gap ("should be captured from the official realtime pages or
  verified experimentally"). `SubscribeAccounts`/`SubscribeOrders`/
  `SubscribePositions`/`SubscribeTrades`/`SubscribeContractQuotes`/
  `SubscribeContractTrades` and the `GatewayUser*`/`GatewayQuote`/
  `GatewayTrade` event names come from independent third-party sources
  cross-referenced during the initial build, not from the reference doc.
  Your `python -m trader_agent status` run is the real test of these.

If anything above turns out to not match TopstepX's real behavior, that's
expected -- report it and it gets fixed.

**ST1 additions**, now that the reference doc documents the Order
endpoints (section 6):

- **Order status is derived, not trusted from a provider enum.** The
  reference explicitly flags the full order-status enum as unverified
  (section 12). Rather than guess what a numeric status code means,
  `OrderManager`/`TopstepXProvider` derive EdgeLog's own
  working/partially_filled/filled state from `fillVolume` vs. `size`, and
  set canceled/rejected only from EdgeLog's own place/cancel call
  outcomes -- never from a reconciled search result. Your `python -m
  trader_agent order` run against a real Practice order is the real test
  of whether this derivation matches reality.
- **The realtime `GatewayUserOrder` payload shape is cross-referenced,
  not confirmed**, same caveat as the SignalR method/event names above.
  `OrderManager.apply_realtime_update` is deliberately defensive: it only
  acts when it can positively match a `customTag` it generated itself,
  and never raises on a payload shape it doesn't recognize.
- **`AccountViolation`/`OutsideTradingHours`/other place-order error
  codes are logged verbatim from `errorMessage`, not translated** into
  friendlier text -- the exact wording TopstepX returns for each isn't
  independently confirmed, so this code surfaces it as-is rather than
  guessing a mapping.

## Not yet built (intentionally out of scope for ST0/ST1)

- Running as an actual Windows Service (this is a foreground console
  process for now).
- Any order type other than a Practice-account limit order (market,
  stop, trailing-stop, bracket orders) -- `place_limit_order` is the only
  submission method that exists; there is no generic "place order with a
  type parameter" anywhere in this codebase.
- Any strategy, signal, or automated decision-making of any kind. Every
  order requires a human to construct it via `order` and type `CONFIRM`.
  ST2 (issue #27) adds an observe-only strategy engine with no execution
  capability; ST3 (issue #28) is the first issue that connects a strategy
  to execution, and only through an independent risk engine.
- Any code path that lets EdgeLog cloud influence trading (by design,
  permanently -- not just "not yet").
- Reading/writing EdgeLog cloud data at all. This agent is fully
  standalone; a read-only status sync to EdgeLog cloud is a reasonable
  future addition but wasn't required by ST0/ST1's acceptance criteria
  and would mean touching `backend/`, which these issues deliberately do
  not.
