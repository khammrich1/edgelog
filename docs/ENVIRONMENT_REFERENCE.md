# EdgeLog Operations Runbook — non-secret environment reference

Updated: 2026-10-20. Read this BEFORE giving EdgeLog deployment or testing commands. This is documentation, NOT a runtime .env file. Never commit secrets.

## Identity and architecture
- Repository: https://github.com/khammrich1/edgelog
- DEV: https://d.edgelog.trade
- PROD: https://edgelog.trade
- Backend: FastAPI / Uvicorn; frontend: Vue 3 / Vite; database: PostgreSQL / Alembic.
- **Public DEV is DigitalOcean App Platform**, reached through `d.edgelog.trade` CNAME `jellyfish-app-3r6dd.ondigitalocean.app` (owner DNS and DigitalOcean dashboard evidence, 2026-10-20). The App Platform dashboard shows GitHub activity for `khammrich1/edgelog/main`. Do not assume droplet DEV is the public DEV runtime.
- **PROD is hosted on the droplet** `edgelog-prod` (observed public outbound IPv4 `24.144.95.61`). Public DEV is hosted on DigitalOcean App Platform. The PROD droplet also contains a separate `/home/edgelog/dev` checkout and `edgelog-dev.service` for local testing; those do **not** constitute the public DEV deployment.

## Verified server layout (owner terminal, 2026-10-20)
- Host: `edgelog-prod`, login `edgelog`. **This is the PROD droplet**, which also has a separate local DEV service/checkout. Public DEV runs on App Platform.
- Local test/DEV checkout on PROD droplet (not public DEV): `/home/edgelog/dev`; observed HEAD `b6bae1716b609b9b6168e939fe72b48caaa37d30` (matches PR #91 head).
- PROD checkout: `/home/edgelog/app`; observed HEAD `a2b314154179124e947b2e1de4da2201bf7add47`.
- Local DEV/test backend systemd unit on PROD droplet: `edgelog-dev.service` (active/running); not the public DEV runtime.
- PROD backend systemd unit: `edgelog-backend.service` (active/running).
- Local DEV/test frontend build destination on PROD droplet: `/var/www/d.edgelog.trade/`; not the public DEV frontend.
- PROD frontend build destination: `/var/www/edgelog/`.
- These are checkout revisions, not independent proof of deployed running backend/frontend revisions.
- Note: the checked-in `deploy/nginx/edgelog.conf` refers to `/var/www/edgelog/frontend`, but the observed production deploy wrapper publishes to `/var/www/edgelog/`. Inspect live Nginx config to resolve this drift.

## DEV runtime verification (owner terminal, 2026-10-20)
- `systemctl show edgelog-dev`: `WorkingDirectory=/home/edgelog/dev/backend`.
- `ExecStart=/home/edgelog/dev/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2`.
- `ActiveEnterTimestamp=Tue 2026-10-20 16:56:09 UTC` (09:56:09 PDT).
- `git -C /home/edgelog/dev log -1`: `b6bae17`, 2026-10-19 20:31:39 UTC, "Address PR #91 review blocker: grouping/P&L/scoping correctness fixes".
- `curl https://d.edgelog.trade/`: HTTP 200.
- Direct droplet DEV FastAPI `http://127.0.0.1:8001/openapi.json` advertises `/api/v1/journal/reconciliation/preview`; unauthenticated POST returns HTTP 403.
- Droplet local Nginx (HTTPS `--resolve d.edgelog.trade:443:127.0.0.1`) returns HTTP 403 for the same POST; droplet Nginx `location /api/` proxies to port 8001 without stripping the prefix.
- **Public App Platform** `https://d.edgelog.trade/api/v1/journal/reconciliation/preview` returns HTTP 404, and `/api/openapi.json` returns HTTP 404. These results do not prove PR #91 is missing from App Platform: inspect its own deployed components and routing before concluding cause.
- Public DNS: `d.edgelog.trade` CNAME `jellyfish-app-3r6dd.ondigitalocean.app`, with observed IPv4 ingress `162.159.140.98`, `172.66.0.96`; these match the DigitalOcean dashboard static ingress IPs. **Do not recommend changing DNS to the droplet.**
- DigitalOcean App Platform dashboard Recent Activity shows pushes to `khammrich1/edgelog/main`, including `49d16b1` at 10:25:50 AM (2026-10-20). Push activity alone is not proof of deployed SHA; app deployment details have not been independently checked.
- Evidence supports PR #91 backend checkout being active after its latest commit; it does NOT independently establish that frontend static assets are from the same revision or that the reconciliation API works. Test endpoint next.

## Actual deployment functions (observed via `type`)
- `dev-el-deploy pr N`: cd `~/dev`; resolve PR branch using `gh pr view`; fetch; `git checkout -B`; **`git reset --hard origin/<branch>` (discards uncommitted changes in DEV checkout)**; install backend requirements; **`alembic upgrade head` (DB migration)**; restart `edgelog-dev`; `npm install`; `npm run build`; `rsync -av --delete dist/ /var/www/d.edgelog.trade/`; `nginx -t`; reload Nginx; show service status.
- `el-deploy`: cd `~/app`; `git pull --ff-only origin main`; install backend requirements; **`alembic upgrade head`**; restart `edgelog-backend`; `npm install`; `npm run build`; `rsync -av --delete dist/ /var/www/edgelog/`; `nginx -t`; reload Nginx; show service status.
- Both wrappers are shell functions defined in the user's shell environment; exact defining file not yet identified. **They operate on the PROD droplet; the DEV wrapper affects its local test service, not public App Platform DEV.**
- Neither wrapper verifies an HTTP response after deployment; perform separate health and acceptance checks.
- Before running DEV wrapper, inspect uncommitted work and migrations; never run PROD wrapper without owner approval.

## Authoritative delivery workflow — OWNER-CONFIRMED (2026-10-20)
1. GitHub issue -> implementation branch and PR -> code/test review.
2. **With explicit owner approval, merge PR into `main`.** This triggers automatic deployment of `main` to public DEV on DigitalOcean App Platform (`d.edgelog.trade`).
3. Confirm the App Platform deployment succeeds and test the deployed feature on **public DEV**. Failed acceptance -> fix through a new PR/approved follow-up, merge to `main`, wait for App Platform redeploy, retest. Do not assume a GitHub push proves deployment.
4. **Only after owner acceptance on DEV and separate explicit PROD deployment authorization**, SSH into the PROD droplet and run the documented **`el-deploy`** command. This deploys approved `main` to `edgelog.trade`.
5. Verify PROD functionality and record deployed revision and acceptance results.
**Do not use `dev-el-deploy pr N` as the public DEV workflow.** It only operates on a local test service on the PROD droplet. Do not deploy PROD without authorization.
Note: `docs/DEVELOPMENT_WORKFLOW.md` and any other workflow references that prescribe PR-to-droplet-DEV before merge are **outdated and require reconciliation** against this owner-confirmed process.

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
- Owner-confirmed release path: **merge PR #91 into `main` (authorized by owner) -> automatic App Platform DEV deployment -> owner acceptance on public DEV -> owner-authorized `el-deploy` on PROD droplet**. Do not use `dev-el-deploy pr 91` for public DEV. Verify actual merge/deployment/test status rather than assuming completion.
- No broker writes, production changes, or historical journal mutation authorized.

## Outstanding runtime facts to record once verified
- Contents/paths of `dev-el-deploy` and `el-deploy` wrappers (without secrets).
- PROD systemd unit WorkingDirectory and ExecStart; DEV service port 8001 confirmed.
- Droplet DEV Nginx config inspected and functional locally; **public DEV App Platform app spec, deployed revision and routing still need inspection**.
- DB identifiers and env-file **paths only**, no credentials.
- Actual Nginx document roots, log paths, and independently verifiable deployed SHA for each environment.
- Rollback process supported by the real deployment scripts.

When evidence conflicts, verify actual host configuration rather than treating an old setup guide as current reality.

## Public DEV App Platform routing (owner dashboard, 2026-10-20)
- Backend component routing rules: `/api` and `/health`, both **Match all domains** and **Full path preserved**.
- Backend component Public HTTP Port: `8080`.
- The App Platform `/api` routing rule already exists and preserves the prefix; **do not add a duplicate rule or enable prefix stripping** to address the reconciliation endpoint 404.
- Public DEV `POST /api/v1/journal/reconciliation/preview` returned HTTP 404, whereas the separate droplet local backend and Nginx returned HTTP 403 without authentication. **Cause remains unverified**; next read-only diagnostic is to check the registered routes inside the App Platform backend runtime, not the PROD droplet.
- Suggested App Platform backend Console diagnostic: `python -c "from app.main import app; print('\\n'.join(r.path for r in app.routes if 'reconciliation' in r.path))"`. The command has **not** been executed or verified in App Platform.

## Lessons learned / avoid repeat troubleshooting (2026-10-20)

**Verified topology**
- PROD: droplet `edgelog-prod`, serving `edgelog.trade`; its `/home/edgelog/dev` checkout and port 8001 are **local test services on the PROD droplet**, not the public DEV deployment.
- Public DEV: DigitalOcean App Platform app associated with `jellyfish-app-3r6dd.ondigitalocean.app`, serving `d.edgelog.trade`. Its backend web-service component is `edgelog-backend`, public HTTP port `8080`. The owner confirmed App Platform follows `khammrich1/edgelog/main` for deployments. Do not mistake GitHub Recent Activity pushes for proof of successful deployment.
- App Platform backend routing: `/api` and `/health`, **full path preserved** and **all domains**. DNS and these ingress rules were verified correct. Do not change them to fix a missing application route.

**Root cause of the Oct 20 404 (verified at the time of investigation)**
- Direct PROD-droplet-local test backend `127.0.0.1:8001` registered `/api/v1/journal/reconciliation/preview` and returned 403 unauthenticated; local droplet Nginx also returned 403. Those tests said **nothing about the App Platform runtime**.
- Public App Platform `POST https://d.edgelog.trade/api/v1/journal/reconciliation/preview` returned 404.
- In the **actual App Platform backend Console**, `python -c "from app.main import app; print('\\n'.join(r.path for r in app.routes if 'reconciliation' in r.path))"` printed no routes. This directly demonstrated the running public DEV FastAPI app had **not registered** the endpoint; the 404 was not explained by DNS or prefix rewriting.
- PR #91 was still pending merge/deployment verification when owner stated intent to merge it so App Platform would deploy from `main`. **Do not assert it has merged, deployed or passed acceptance until checked.**

**Fast diagnostic workflow — start here next time**
1. Identify target environment and hosting **before any SSH command**. For public DEV, open DigitalOcean App Platform's `edgelog-backend` Console, not the PROD droplet. For PROD, use the droplet.
2. Check public endpoint status. For unauthenticated reconciliation preview POST, expect 403 if the route is registered and protected; 404 indicates missing route or routing issue. Do not use `/api/openapi.json` as the sole test: FastAPI's OpenAPI may live at `/openapi.json` and ingress may not expose it.
3. In App Platform backend Console, inspect registered routes directly (command above). If absent, inspect **that component's deployed SHA, source branch, build/deploy status, and code**, not droplet checkout SHAs or Nginx. App Platform console route inspection is read-only.
4. If registered in App Platform but public URL still returns 404, inspect App Platform ingress mapping and application logs for that request. Preserve `/api` prefix unless evidence shows otherwise.
5. **Owner-confirmed workflow:** authorized merge to `main` automatically deploys public DEV App Platform; verify route registration and public unauthenticated POST, then owner tests authenticated behavior with synthetic data. Only after DEV PASS and explicit authorization run `el-deploy` on the PROD droplet. **Do not mark PR #91/issue #80 accepted merely because route exists or tests pass.**
6. Record the exact public DEV deployed commit and test results in this file, status and EOD. Avoid conflating `dev-el-deploy pr N` (droplet-local) with public App Platform deployment.

**Operational gap:** Prior environment documentation incorrectly treated the PROD droplet's local DEV service as public DEV. This caused unnecessary Nginx, DNS and droplet testing. Public DEV deployment/rollback commands and precise component source/build settings still require confirmation; do not invent them.
