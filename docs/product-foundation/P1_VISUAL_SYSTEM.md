# P1 — EdgeLog Product Shell & Visual System

Implementation brief: issue #35.

## Objective

Make the existing EdgeLog application look and feel like a coherent premium trading journal before adding more Strategy Trader machinery.

**Brand:** Find Your Edge.  
**Core loop:** TRADE → REFLECT → IMPROVE

## Visual direction

- Onyx / near-black application field
- Graphite cards and surfaces
- Restrained copper accents
- Steel dividers, borders and grid
- Off-white primary typography
- Green/red reserved for meaningful P&L/state
- Narrow left navigation rail
- Condensed uppercase labels/headings where appropriate
- Dense, readable professional trading-journal hierarchy

## Scope

Audit the current frontend first. Establish reusable tokens/components and apply them consistently to the existing shell/navigation, headers, typography, spacing, cards/panels, buttons, forms, tabs, tables/lists, badges/status, existing dialogs/dropdowns, and loading/empty/error states.

Apply the system across the major existing screens without changing their underlying product behavior.

## Guardrails

- Preserve working routes, actions and data.
- Do not start Strategy Trader ST2+.
- Do not turn the product into generic oversized SaaS cards.
- Avoid page-specific CSS patches where a shared token/component belongs.
- Do not deploy production.
- Keep this an owner-testable vertical slice.

## Owner gate

Claude implements on the existing P1 PR. Nova reviews. Kyle deploys that exact PR to DEV and gives PASS/FAIL. FAIL is fixed on the same PR. PASS permits merge.
