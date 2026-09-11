# EdgeLog Mentorship

## Purpose
Mentorship adds accountability between a mentor and a defined group of mentees without turning EdgeLog into a generic social network, signal room, copy-trading product, or P&L leaderboard.

Primary mentor question: **Did each mentee prepare, how are they showing up today, and what did they actually trade?**

## Core loop
1. Mentee opens EdgeLog for the trading day.
2. Before the normal trading workflow, the mentee completes a short daily check-in.
3. The check-in updates the canonical Trading Day record.
4. Mentor dashboard shows check-in state and a compact shared readiness summary.
5. Recorded trades appear in mentor-visible activity according to sharing settings.
6. Mentor can open a mentee detail page for preparation, trades, debrief status, and recent process consistency.
7. A no-trade day is a valid process outcome.

## Daily check-in
Target completion time: 30-90 seconds.

Suggested fields:
- mood / emotional state
- energy / readiness
- sleep quality
- clarity / confidence
- market bias or plan
- daily risk guardrail
- one short intention: "What do you need to do well today?"
- optional note to mentor
- optional no-trade-day selection

This is an accountability tool, not a trading permission or suitability system.

## Mentor group page
Each active mentee gets a compact card/row showing, where permitted:
- username / display name
- avatar or initials
- checked in today: yes/no + time
- shared mood/readiness
- sleep quality if shared
- trading-day state: not started / trading / done / no-trade
- trade count today
- shared daily P&L and/or R if enabled
- last activity
- attention indicator for a missing check-in or user-submitted readiness/discipline concern

Do not rank mentees by P&L, win rate, trade count, or activity.

## Mentee detail page
Header:
- identity
- group membership
- today's check-in state
- shared readiness summary
- current trading-day state

Today:
- check-in summary
- market plan / bias if shared
- risk guardrail if shared
- today's trades
- trade status, symbol, direction, setup and result where available
- daily debrief status

History:
- recent check-in consistency
- recent trading days
- recent trades
- no-trade days

## Privacy
Mentorship requires server-side authorization and explicit visibility boundaries.

Distinguish:
1. mentor-visible accountability fields
2. mentor-visible trade fields
3. private journal / psychology fields
4. optional group-visible profile fields

Private journal and psychology content is private by default.

## Data model direction
Do not duplicate journal or trade data for mentorship.

Future mentorship entities may include:
- mentorship_groups
- mentorship_memberships
- mentorship_roles
- mentorship_visibility_preferences

Daily check-in data should reuse or extend the canonical Trading Day model. Mentor-visible trades should reference canonical Trade records.

## Sequence
Mentorship is documented early because it affects Daily Journal, Trade Lifecycle, privacy and profiles, but it should not be implemented before prerequisites.

Recommended order:
1. Foundation
2. Daily Journal Core with check-in-compatible Trading Day model
3. Trade Lifecycle
4. Daily Debrief
5. Mentorship groups, roles and visibility
6. Mentor group dashboard
7. Mentee detail view
