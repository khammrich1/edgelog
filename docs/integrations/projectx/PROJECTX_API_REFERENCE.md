# ProjectX / TopstepX API Reference for EdgeLog

> **Purpose:** Offline implementation reference for Claude while working on EdgeLog Strategy Trader issues #25-#30.
>
> **Source:** Derived from the official ProjectX Gateway API documentation at gateway.docs.projectx.com, reviewed 2026-09-28. This is an EdgeLog-maintained reference, **not an official OpenAPI specification**. If this file conflicts with current ProjectX documentation, the official documentation is authoritative.
>
> **Security:** Never place a real username, API key, bearer token, or account secret in this document, Git, logs, browser storage, or the EdgeLog cloud database.

## 1. TopstepX connection URLs

- REST API base: `https://api.topstepx.com`
- User realtime hub: `https://rtc.topstepx.com/hubs/user`
- Market realtime hub: `https://rtc.topstepx.com/hubs/market`

Realtime uses SignalR/WebSocket-style connections. The user hub provides account/order/position updates. The market hub provides quotes, market trades, DOM, and related market events.

## 2. Authentication

### Login with API key

`POST /api/Auth/loginKey`

Request:
```json
{
  "userName": "<platform-login-username>",
  "apiKey": "<secret-api-key>"
}
```

Important:
- `userName` is the trading-platform username, not email and not account name/ID.
- API-key login is the supported way to obtain a session token.
- Successful response returns a JWT/session token.
- Token lifetime is 24 hours.
- Reuse one token for REST and realtime connections.
- A failed login can still return HTTP 200; inspect `success`, `errorCode`, and `errorMessage`.
- Missing `userName` or `apiKey` can return HTTP 400.

Representative response shape:
```json
{
  "token": "<session-token>",
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}
```

Known login error codes:
- 3 InvalidCredentials
- 7 AgreementsNotSigned
- 9 ApiSubscriptionNotFound
- 10 ApiKeyAuthenticationDisabled

### Validate/refresh session

`POST /api/Auth/validate`

Authenticated request. Successful response includes `newToken`.

Representative response:
```json
{
  "success": true,
  "errorCode": 0,
  "errorMessage": null,
  "newToken": "<new-token>"
}
```

## 3. Rate limits

- `POST /api/History/retrieveBars`: 50 requests / 30 seconds
- All other endpoints: 200 requests / 60 seconds
- Exceeding a limit returns HTTP 429. Back off rather than retrying aggressively.

## 4. Accounts

### Search accounts

`POST /api/Account/search`

Request:
```json
{
  "onlyActiveAccounts": true
}
```

Representative account fields:
- `id`
- `name`
- `balance`
- `canTrade`
- `isVisible`

Realtime account payloads may also expose `simulated`.

Do not infer that an account is safe/eligible for automated execution from its name alone. Check provider state and EdgeLog's own allowed-account policy.

## 5. Contracts / market-data REST

ProjectX documents four market-data REST operations:
- Retrieve Bars
- Search for Contracts
- Search for Contract by ID
- List Available Contracts

### List available contracts

`POST /api/Contract/available`

Request:
```json
{
  "live": false
}
```

Representative contract fields:
- `id` — provider contract ID
- `name`
- `description`
- `tickSize`
- `tickValue`
- `activeContract`
- `symbolId`

Example shape:
```json
{
  "id": "CON.F.US.BP6.U25",
  "name": "6BU5",
  "description": "British Pound (Globex): September 2025",
  "tickSize": 0.0001,
  "tickValue": 6.25,
  "activeContract": true,
  "symbolId": "F.US.BP6"
}
```

For EdgeLog, resolve the current active contract from provider data. Do not hard-code an expiring MNQ contract ID.

### Retrieve historical bars

`POST /api/History/retrieveBars`

Request fields:
- `contractId`
- `live` boolean
- `startTime`
- `endTime`
- `unit`
- `unitNumber`
- `limit`

Aggregation unit enum:
- 1 Second
- 2 Minute
- 3 Hour
- 4 Day
- 5 Week
- 6 Month

Maximum bars per request: 20,000.

## 6. Orders

ProjectX documents order operations for searching, placing, modifying, and cancelling orders. Strategy code must never call these endpoints directly; EdgeLog's local execution adapter/order manager owns provider calls.

### Place order

`POST /api/Order/place`

Request fields:
- `accountId` integer — required
- `contractId` string — required
- `type` integer — required
- `side` integer — required
- `size` integer — required
- `limitPrice` decimal/null
- `stopPrice` decimal/null
- `trailPrice` decimal/null
- `customTag` string/null — optional, must be unique across account
- `stopLossBracket` object/null
- `takeProfitBracket` object/null

Order type enum:
- 1 Limit
- 2 Market
- 4 Stop
- 5 TrailingStop
- 6 JoinBid
- 7 JoinAsk

Order side enum:
- 0 Bid / buy
- 1 Ask / sell

Representative limit-order request:
```json
{
  "accountId": 123,
  "contractId": "<active-contract-id>",
  "type": 1,
  "side": 0,
  "size": 1,
  "limitPrice": 25000.00,
  "stopPrice": null,
  "trailPrice": null,
  "customTag": "edgelog-<unique-id>",
  "stopLossBracket": null,
  "takeProfitBracket": null
}
```

Representative response:
```json
{
  "orderId": 9056,
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}
```

Place-order error codes:
- 0 Success
- 1 AccountNotFound
- 2 OrderRejected — inspect `errorMessage`
- 3 InsufficientFunds
- 4 AccountViolation
- 5 OutsideTradingHours
- 6 OrderPending
- 7 UnknownError
- 8 ContractNotFound
- 9 ContractNotActive
- 10 AccountRejected

#### Brackets

Bracket objects contain:
- `ticks`
- `type` using the same OrderType enum

Account bracket mode matters:
- **Position Brackets** (default): bracket objects are not accepted on `Order/place`.
- **Auto OCO Brackets**: `stopLossBracket` and `takeProfitBracket` can attach to the order.

If bracket objects are sent while Position Brackets mode is active, the order is rejected with errorCode 2. The rejected order may still have an `orderId`, so never equate presence of an order ID with successful acceptance.

#### Trailing-stop warning

For type 5, `trailPrice` is an **absolute price level**, not a distance. The server derives the tick distance from last traded price. It must align to tick size. Do not pass a distance such as `0.06` when the API expects a price level.

### Modify order

`POST /api/Order/modify`

Fields:
- `accountId` required
- `orderId` required
- `size` optional
- `limitPrice` optional
- `stopPrice` optional
- `trailPrice` optional for trailing stops

Trailing-stop `trailPrice` has the same absolute-price semantics described above.

### Cancel order

`POST /api/Order/cancel`

Request:
```json
{
  "accountId": 123,
  "orderId": 456
}
```

Cancel error codes:
- 0 Success
- 1 AccountNotFound
- 2 OrderNotFound
- 3 Rejected
- 4 Pending
- 5 UnknownError
- 6 AccountRejected

Known errorCode 6 messages include:
- `Follower accounts cannot cancel orders`
- `Live accounts not supported`

The documented cancel endpoint supports simulated accounts that are not follower accounts.

### Search orders

`POST /api/Order/search`

Request:
```json
{
  "accountId": 123,
  "startTimestamp": "<ISO-8601>",
  "endTimestamp": "<ISO-8601-or-null>"
}
```

Representative order fields:
- `id`
- `accountId`
- `contractId`
- `symbolId`
- `creationTimestamp`
- `updateTimestamp`
- `status`
- `type`
- `side`
- `size`
- `limitPrice`
- `stopPrice`
- `fillVolume`
- `filledPrice`
- `customTag`

## 7. Positions

ProjectX documents position search, full close, and partial close operations.

### Search open positions

`POST /api/Position/searchOpen`

Request:
```json
{
  "accountId": 123
}
```

Representative position fields:
- `id`
- `accountId`
- `contractId`
- `creationTimestamp`
- `type`
- `size`
- `averagePrice`

### Partial close

`POST /api/Position/partialCloseContract`

Request fields:
- `accountId`
- `contractId`
- `size`

A documented `AccountRejected`/live-account restriction applies to these simulated-account execution operations. Treat provider rejection as authoritative.

## 8. Trades

### Search trades

`POST /api/Trade/search`

Request:
```json
{
  "accountId": 123,
  "startTimestamp": "<ISO-8601>",
  "endTimestamp": "<ISO-8601-or-null>"
}
```

Realtime/documented trade payload fields include:
- `id`
- `accountId`
- `contractId`
- `creationTimestamp`
- `price`
- `profitAndLoss`
- `fees`
- `side`
- `size`
- `voided`
- `orderId`

Use provider trade/order IDs for reconciliation/idempotency metadata; do not replace EdgeLog's canonical Trade/TradeEntry/TradeExit IDs with provider IDs.

## 9. Realtime / SignalR

ProjectX realtime uses two hubs.

### User hub
Provides updates involving:
- accounts
- orders
- positions
- trades/balances as documented by the realtime reference

Representative realtime order fields:
- `id`
- `accountId`
- `contractId`
- `symbolId`
- `creationTimestamp`
- `updateTimestamp`
- `status`
- `type`
- `side`
- `size`
- `limitPrice`
- `stopPrice`
- `fillVolume`
- `filledPrice`
- `customTag`

### Market hub
Provides market events such as:
- quotes
- market trades
- DOM-related events

Representative quote fields include:
- `symbol`
- `symbolName`
- `lastPrice`
- `bestBid`
- `bestAsk`
- `change`
- `changePercent`
- `open`
- `high`
- `low`

For execution safety, EdgeLog Trader must maintain a local timestamp for the last valid market update and enter a stale/fault state when freshness exceeds the configured threshold.

## 10. EdgeLog implementation rules

These are **EdgeLog architecture rules**, not claims about the ProjectX API itself.

1. Actual trading/order origination lives in the local EdgeLog Trader Agent on the user's personal Windows device.
2. EdgeLog cloud is journal/configuration/analytics/read-only status; it must not become a remote order relay.
3. Topstep username/API key/session token stay local.
4. Strategy code emits a normalized Trade Plan. It cannot call ProjectX endpoints.
5. Independent local risk engine approves/rejects a Trade Plan.
6. Local execution adapter converts an approved plan to provider requests.
7. Every provider request uses idempotency/duplicate-submission protection where possible; `customTag` is useful but does not replace local state reconciliation.
8. On startup/reconnect, query/reconcile provider orders and positions before enabling execution.
9. Presence of `orderId` does not prove success; always inspect `success`, `errorCode`, and `errorMessage`.
10. Never invent P&L, fills, order status, tick size/value, or active contract when provider data is unavailable.
11. Practice/simulated account is the initial development target.
12. AUTO TRADING defaults OFF after restart, strategy-version change, credential change, or unresolved reconciliation fault.
13. Audit all strategy signals, risk decisions, provider requests, acknowledgements, fills, modifications, cancellations, faults, and recovery actions without logging secrets.
14. Automated executions must reconcile into EdgeLog's canonical Trade / TradeEntry / TradeExit model.

## 11. ST0-ST4 mapping

### ST0 / #25
Use:
- Auth/loginKey
- Auth/validate
- Account/search
- Contract endpoints
- Market realtime hub
- User realtime hub
- historical bars only if needed

No order placement.

### ST1 / #26
Add:
- Order/place — manual-confirmed Practice limit only
- Order/search
- Order/cancel
- realtime order updates
- duplicate protection and kill controls

### ST2 / #27
No new provider execution capability required. Build deterministic strategy contract/observe-only engine against normalized market data.

### ST3 / #28
Connect accepted strategy -> independent risk engine -> local execution adapter. Practice only. Reconcile order/position state before resuming after faults/restarts.

### ST4 / #29
Expose local-agent status/configuration through EdgeLog UI and reconcile provider executions into canonical journal records. Strategy ID/version/source must be retained for analytics #30.

## 12. Gaps / do not guess

This reference intentionally does not fabricate undocumented details. Before implementing something not described here, mark it as a documentation gap rather than guessing. In particular:
- exact SignalR client subscription method/event names should be captured from the official realtime pages or verified experimentally before hard-coding;
- complete enum values not reproduced here should be treated as unknown until verified;
- full-close position endpoint details should be verified before implementation;
- contract search/by-ID request schemas should be verified before implementation;
- any brokerage/live-account execution capability must be separately verified; do not infer it from simulated-account endpoints.

## 13. Official source pages used to derive this reference

- ProjectX Gateway API introduction
- Getting Started
- Authenticate with API key
- Validate Session
- Connection URLs
- Rate Limits
- Placing Your First Order
- API Reference index
- Account / Search for Account
- Market Data / Retrieve Bars / Contract references
- Orders / Place / Modify / Cancel / Search
- Positions / Search Open / Partial Close
- Trades / Search
- Realtime Updates / Real Time Data Overview

Last reviewed: 2026-09-28.
