# Green Bread Development Workflow

This repository follows the Green Bread standard delivery workflow.

## Vertical slices

A **vertical slice** is a small, coherent, end-to-end, owner-testable increment that crosses whatever layers are necessary to deliver a real behavior.

Do not divide feature work into disconnected backend-first/frontend-later phases when an end-to-end slice can be built and tested instead. Large scopes should be decomposed when that makes implementation, review, deployment, or owner testing safer and clearer.

For Strategy Trader, **ST means Strategy Trader**. ST0, ST1, ST2, etc. are Strategy Trader slices.

## Standard work cycle

1. Owner + assistant scope and review the work.
2. Break the scope into vertical slices when needed.
3. Assistant creates/updates the **authoritative GitHub Issue/specification** for the current slice.
4. **Claude creates the implementation PR** from that issue, or uses an already-existing implementation PR when one intentionally exists.
5. Claude implements and updates that same PR.
6. Assistant reviews the implementation against the issue/spec.
7. Deploy the exact PR to DEV with `dev-el-deploy pr <PR_NUMBER>`.
8. Owner manually tests the DEV build.
9. **FAIL:** fix the same PR, redeploy, and retest.
10. **PASS:** merge the PR to `main`.
11. Deploy `main` to production as a separate explicit step.
12. Start the next slice.

The **Issue is the authoritative scope/specification record**. The **PR is the implementation/testable unit**. Do not create an implementation PR merely while scoping a new issue; the normal handoff is Issue → Claude implementation PR.

## Owner acceptance

A slice is not complete merely because code exists, Claude self-reviewed it, or automated tests/build pass. Major milestones require owner testing and an explicit PASS before merge.

Do not silently broaden a failed owner test into a redesign. Fix the concrete failure on the same PR unless the owner explicitly moves the problem into a new slice.

## EdgeLog deployment commands

DEV exact-PR deployment:

```bash
dev-el-deploy pr <PR_NUMBER>
```

Production deployment after the accepted PR is merged:

```bash
el-deploy
```

## EdgeLog product constraints that affect implementation

### Manual journaling is intentional

EdgeLog is manual-first by design. Automation may reduce clerical entry, but must not remove deliberate review.

- AI/screenshot extraction may prefill candidate data; the trader confirms it.
- Future execution integration may prefill objective execution facts; it must not silently complete the journal/reflection.
- Analytics are downstream of the trader's deliberate journal.

Core loop: **Plan → Trade → Journal → Reflect → Improve**.

### Strategy Trader

Strategy Trader must support:

**Plan → Validate → Take Trade → Track → Journal/Learn**

Order origination stays on the trader's personal device. TopstepX credentials stay local. EdgeLog cloud is not an order relay.
