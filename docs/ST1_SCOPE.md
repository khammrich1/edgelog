# ST1 — Practice Limit-Order Execution and Kill Controls

Implements GitHub issue #26.

## Goal
Prove the local Trader Agent can safely execute and manage a manually approved Practice-account MNQ limit order through TopstepX/ProjectX.

## Required scope
- Practice account only; MNQ; limit orders only.
- Manual order construction and exact review of account, contract, side, quantity, and price.
- Explicit confirmation before submission.
- Local provider submission; provider order ID and timestamps.
- Working / filled / canceled / rejected state tracking.
- Cancel a working order.
- Duplicate-submission/idempotency protection.
- Hard POC maximum quantity.
- Global AUTO TRADING OFF state.
- Local emergency stop / kill control.
- Disconnect/stale-data submission blocking.
- Full local audit trail.
- No cloud/server order origination.

## Owner acceptance
Claude implements in this PR and stops for owner testing. Do not merge, deploy production, or start #27.
