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
7. After assistant code review and required automated checks, **owner explicitly authorizes merging the PR to `main`**.
8. Merge to `main` triggers **automatic public DEV deployment** on DigitalOcean App Platform (`https://d.edgelog.trade`). Confirm the deployment succeeded and record its commit.
9. Owner manually tests **public DEV**. **FAIL:** correct the defect via an approved follow-up PR, merge to `main` with owner authorization, wait for App Platform redeployment, and retest. **PASS:** owner explicitly accepts the DEV build.
10. **Only after DEV PASS and separate owner authorization**, run `el-deploy` on the **PROD droplet** to deploy approved `main` to `https://edgelog.trade`.
11. Verify PROD and record deployed revision and smoke-test results.
12. Start the next slice.

The **Issue is the authoritative scope/specification record**. The **PR is the implementation/testable unit**. Do not create an implementation PR merely while scoping a new issue; the normal handoff is Issue → Claude implementation PR.

## Owner acceptance

A slice is not complete merely because code exists, Claude self-reviewed it, or automated tests/build pass. Major milestones require owner testing and an explicit PASS on public DEV **before production deployment**. Merging to `main` precedes public DEV acceptance because App Platform automatically deploys `main`. Owner approval is required for both merge and PROD deployment.

Do not silently broaden a failed owner test into a redesign. Fix the concrete failure in a narrowly scoped follow-up PR and retest public DEV; never deploy a failed slice to PROD.

## EdgeLog deployment commands

**Public DEV:** Merge an owner-approved PR into `main`; DigitalOcean App Platform automatically deploys `main` to `d.edgelog.trade`. Verify deployment and owner-test there. No droplet command is needed for public DEV.

**PROD:** After owner DEV PASS and separate PROD authorization, SSH to the PROD droplet and run:

```bash
el-deploy
```

The legacy `dev-el-deploy pr <PR_NUMBER>` function targets a **local test service on the PROD droplet**, not public DEV. Do not use it as the normal DEV release path. Do not change DNS or App Platform ingress to mimic droplet routing.

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
