# EdgeLog / LockedIn — Product Direction and DEV Gate (2026-10-11)

**Status:** Owner-confirmed product direction; not shipped-feature evidence. **EdgeLog** remains the working name. **LockedIn / lockedin.trade** is an unapproved rebrand candidate; no rename, domain, DNS, or trademark decision has been made.

## Product promise

**Get Dialed In. Stay Locked In.** (proposed positioning, not approved brand copy.)

Traders should be able to discover and validate a repeatable edge, teach the application to recognize its objectively defined conditions, plan risk, and receive an opportunity alert. **The trader explicitly approves each entry.** After independently authorized local execution, the system manages the trade by the approved plan when safeguards are proven, reducing chart-watching and reactive intervention.

**Product center: the plan, not the chart.** Live candlesticks are optional context, not the default execution experience. The product aims to reduce avoidable stress and emotional interference, not promise profits or eliminate human oversight.

## Canonical product loop

**DISCOVER → VALIDATE → RECOGNIZE → ALERT → APPROVE → EXECUTE LOCALLY → MANAGE → REVIEW → LEARN**

1. **Discover:** use canonical journal data, market data and observed opportunities to propose trader-defined strategy hypotheses.
2. **Validate:** distinguish a setup match or user checklist grade from a statistically supported edge. Show sample size, costs, uncertainty, out-of-sample and forward-test results; log non-trades and missed signals to address selection bias.
3. **Recognize:** deterministic, immutable-versioned definitions of instrument, timeframe, session, confluences, invalidation and required market data. AI interpretation may advise but is not an execution authority.
4. **Alert:** when a versioned setup qualifies, create a time-bounded **proposal** with evidence and current market freshness. An alert is **not** an order or permission to enter.
5. **Approve:** trader may approve, reject or modify the proposal; changes require a new approved snapshot. Approval binds account, Practice mode, symbol/contract, direction, limit price, quantity, protective stop, targets, max risk, expiry and strategy version. **No unattended automatic entries.**
6. **Execute locally:** the Windows companion independently authenticates the user, validates the approved proposal against fresh provider data, risk constraints, expiry and account, and originates orders directly with TopstepX **Practice**. The cloud stores a pending intent; it must not originate, relay, modify, cancel or trigger broker orders. Duplicate prevention and provider reconciliation are mandatory.
7. **Manage:** apply pre-approved stop, target, trim and breakeven rules **only after** provider-native protection, partial-fill handling, reconnect/restart, stale-data, emergency flatten and fault scenarios are tested and owner accepted (#55). Until then, ST1 remains supervised manual Practice limit order only. Never imply safe walk-away capability prematurely.
8. **Review:** append authoritative events to canonical TradingDay/Trade/TradeEntry/TradeExit; compare plan to actual, ask **Did you touch your trade?**, quantify intervention delta only when determinable, and retain deliberate user-authored psychology/reflection.

## Proposed interaction surfaces

- **Dialed In / Research:** strategy definition, validation, recognition, observe-only signals.
- **Opportunity alert:** setup name/version, instrument, direction, limit entry, stop, targets, size, R/R, evidence/sample-size caveat, current quote age, expiration, **Approve / Reject / Edit**. Show UNKNOWN when data is unavailable.
- **Locked In / Active position:** order and broker-protection state, remaining risk, stop/target, planned management, event feed, connection freshness, cancel/flatten emergency controls. Chart optional; avoid attention-grabbing tick-by-tick UI.
- **Review:** planned vs actual, trade touches, objective execution data and manual reflection.

These are **proposed interface concepts**, not existing UI or approved final naming.

## Delivery status and priority

- **#57 DigitalOcean App Platform DEV:** Owner reported login page loads and `/health` works after Python 3.12 pin and route-prefix adjustments. This is **partial smoke-test evidence**, not full DEV PASS. Exact deployed revision, `/api/v1` routing, Supabase DEV connectivity, Alembic migration state, auth/register/refresh/logout, journal CRUD, persistent screenshots and regression checks remain **unverified**. Do not mark #57 complete.
- Supabase DEV project is separate from droplet PROD. Do not modify PROD DB, DNS, or existing droplet without explicit authorization.
- **#59** tracks the newly clarified alert → explicit approval → local execution workflow. It must reuse #27, #32, #53–#56 and avoid parallel journal stores.
- Existing #43/#49 visual work and #33 ST1 acceptance remain independently gated; do not silently merge.
- **Next immediate work:** complete #57 DEV backend API and database/auth smoke tests, then take the smallest observe-only alert/proposal contract slice from #59 through issue → Claude PR → exact DEV test → owner PASS/FAIL → merge. No live trading authorization.

## Product and safety boundaries

Never guarantee profit, infer fills, label self-declared A+ as validated, silently change a strategy or plan, place an order merely because a signal appeared, or auto-complete the user's reflective journal. Use broker-authoritative data and safe failure behavior. Human entry approval and emergency intervention remain available.
