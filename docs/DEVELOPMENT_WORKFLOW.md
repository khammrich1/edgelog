# Green Bread Development Workflow

This repository follows the Green Bread standard delivery workflow.

## Vertical slices

A **vertical slice** is a small, coherent, end-to-end, owner-testable increment that crosses whatever layers are necessary to deliver a real behavior.

Do **not** divide feature work into disconnected "backend first / frontend later" phases when an end-to-end slice can be built and tested instead.

Large scopes should be decomposed into smaller vertical slices when that makes implementation, review, deployment, or owner testing safer and clearer. Slice numbering may use a workstream prefix and sub-slices (for example ST1, ST1.1, ST1.2).

For the Strategy Trader workstream, **ST means Strategy Trader**. ST0, ST1, ST2, etc. are Strategy Trader vertical slices.

## Standard work cycle

1. Owner + assistant scope and review the work.
2. Break the scope into vertical slices when needed.
3. Create **one work PR for the current slice**.
4. Claude implements and updates that same PR.
5. Assistant reviews the implementation.
6. Deploy the exact PR to DEV.
7. Owner manually tests the DEV build.
8. **FAIL:** fix the same PR, redeploy, and retest.
9. **PASS:** merge the PR to `main`.
10. Deploy `main` to production.
11. Start the next slice.

GitHub Issues are backlog/specification records. The **PR is the operational unit of work** that is implemented, reviewed, deployed, and owner-tested.

## EdgeLog deployment commands

DEV exact-PR deployment:

```bash
dev-el-deploy pr <PR_NUMBER>
```

Production deployment after the accepted PR is merged:

```bash
el-deploy
```

## Owner acceptance

A slice is not complete merely because code exists or automated tests pass. Major milestones require owner testing and an explicit PASS before merge to production.

## Strategy Trader product direction

Strategy Trader work must support EdgeLog's product flow:

**Plan → Validate → Take Trade → Track → Journal/Learn**

Execution infrastructure must remain compatible with that end-to-end flow rather than becoming a disconnected trading tool.
