# EdgeLog Operations Runbook — non-secret environment reference

Updated: 2026-10-20. Read this BEFORE giving EdgeLog deployment or testing commands. This is documentation, NOT a runtime .env file. Never commit secrets.

## Identity and architecture
- Repository: https://github.com/khammrich1/edgelog
- DEV: https://d.edgelog.trade
- PROD: https://edgelog.trade
- Backend: FastAPI / Uvicorn; frontend: Vue 3 / Vite; database: PostgreSQL / Alembic.
- Host observed in owner terminal: `edgelog-prod` (both Git checkouts are on this host). This does not independently establish which running services point to which checkout.

## Observed server layout (owner terminal, 2026-10-20)
- `/home/edgelog/dev/.git` exists: DEV-named repository checkout.
- `/home/edgelog/app/.git` exists: app-named repository checkout (likely PROD).
- Neither checkout's branch/SHA or active service working directory has yet been checked.
- The production deployment guide documents `/var/www/edgelog/backend` as a *setup example* and `/var/www/edgelog/frontend` as a static output directory; do not confuse either with confirmed Git checkout paths.

## Authoritative delivery workflow
Source: `docs/DEVELOPMENT_WORKFLOW.md`.
1. GitHub issue -> Claude implementation PR -> assistant review.
2. Deploy the exact PR to DEV using **`dev-el-deploy pr <PR_NUMBER>`**.
3. Owner manually tests DEV. FAIL -> fix same PR, redeploy, retest.
4. Explicit owner PASS -> merge to main.
5. Separately approved production deployment using **`el-deploy`**.
6. Verify production after deployment.
Never deploy feature code to PROD without owner approval. Never use a generic git pull as a substitute for the documented deployment wrapper.

## How requests reach the application (documented PROD config)
Source: `deploy/nginx/edgelog.conf`.
- HTTPS `edgelog.trade` served by Nginx.
- Vue static frontend: `/var/www/edgelog/frontend`, SPA fallback `/index.html`.
- Same-origin `/api/` forwarded to `http://127.0.0.1:8000` (FastAPI).
- HTTP redirects to HTTPS. Do not remove redirect or change origin to work around CORS.
- PROD guide `DEPLOYMENT.md` describes example systemd service `edgelog-backend`, but actual live service and DEV proxy must be verified on host.

## Non-destructive verification commands
On the host, check checked-out revisions:
```bash
git -C /home/edgelog/dev rev-parse HEAD
git -C /home/edgelog/dev branch --show-current
git -C /home/edgelog/app rev-parse HEAD
```
Inspect how the deploy wrappers work, without executing them:
```bash
type dev-el-deploy
type el-deploy
```
Check service mapping and Nginx config before documenting runtime certainty:
```bash
sudo systemctl list-units --type=service --all | grep -Ei 'edge|uvicorn'
sudo nginx -T 2>/dev/null | grep -n -E 'server_name (d\.)?edgelog\.trade|proxy_pass|root /var/www/edgelog'
```
Do not print runtime .env contents or secrets.

## Current PR acceptance focus (as of 2026-10-20)
- PR #91: `feat/issue-80-reconciliation-preview`.
- GitHub head observed: `b6bae1716b609b9b6168e939fe72b48caaa37d30`; re-fetch before deploying.
- Deployment is **not yet verified**. Use `dev-el-deploy pr 91` to deploy exact PR, then verify deployed revision and run read-only synthetic acceptance tests.
- No broker writes, production changes, or historical journal mutation authorized.

## Outstanding runtime facts to record once verified
- Contents/paths of `dev-el-deploy` and `el-deploy` wrappers (without secrets).
- Actual systemd units, their WorkingDirectory and ExecStart, DEV/PROD port mapping.
- DEV Nginx configuration and frontend static directory.
- DB identifiers and env-file **paths only**, no credentials.
- Where to inspect logs and deployed SHA for each environment.
- Rollback process supported by the real deployment scripts.

When evidence conflicts, verify actual host configuration rather than treating an old setup guide as current reality.
