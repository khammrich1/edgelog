# EdgeLog Operations Runbook — non-secret environment reference

Updated: 2026-10-20. Read this BEFORE giving EdgeLog deployment or testing commands. This is documentation, NOT a runtime .env file. Never commit secrets.

## Identity and architecture
- Repository: https://github.com/khammrich1/edgelog
- DEV: https://d.edgelog.trade
- PROD: https://edgelog.trade
- Backend: FastAPI / Uvicorn; frontend: Vue 3 / Vite; database: PostgreSQL / Alembic.
- **Public DEV is DigitalOcean App Platform**, reached through `d.edgelog.trade` CNAME `jellyfish-app-3r6dd.ondigitalocean.app` (owner DNS and DigitalOcean dashboard evidence, 2026-10-20). The App Platform dashboard shows GitHub activity for `khammrich1/edgelog/main`. Do not assume droplet DEV is the public DEV runtime.
- Droplet `edgelog-prod` (public outbound IPv4 observed `24.144.95.61`) hosts separate DEV and PROD checkouts/services. These do not establish the runtime deployed to public App Platform.

## Verified server layout (owner terminal, 2026-10-20)
- Host: `edgelog-prod`, login `edgelog`. Both DEV and PROD **droplet services** run on this host; public DEV runs on App Platform.
- DEV checkout: `/home/edgelog/dev`; observed HEAD `b6bae1716b609b9b6168e939fe72b48caaa37d30` (matches PR #91 head).
- PROD checkout: `/home/edgelog/app`; observed HEAD `a2b314154179124e947b2e1de4da2201bf7add47`.
- DEV backend systemd unit: `edgelog-dev.service` (active/running).
- PROD backend systemd unit: `edgelog-backend.service` (active/running).
- DEV frontend build destination: `/var/www/d.edgelog.trade/`.
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
- Both wrappers are shell functions defined in the user's shell environment; exact defining file not yet identified.
- Neither wrapper verifies an HTTP response after deployment; perform separate health and acceptance checks.
- Before running DEV wrapper, inspect uncommitted work and migrations; never run PROD wrapper without owner approval.

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
- Public App Platform deployment of PR #91 is **not verified**; the droplet's `dev-el-deploy pr 91` wrapper deploys to the droplet, **not public App Platform**. Do not use that wrapper to claim public DEV deployment. Verify App Platform deployed revision/components and route mapping first.
- No broker writes, production changes, or historical journal mutation authorized.

## Outstanding runtime facts to record once verified
- Contents/paths of `dev-el-deploy` and `el-deploy` wrappers (without secrets).
- PROD systemd unit WorkingDirectory and ExecStart; DEV service port 8001 confirmed.
- Droplet DEV Nginx config inspected and functional locally; **public DEV App Platform app spec, deployed revision and routing still need inspection**.
- DB identifiers and env-file **paths only**, no credentials.
- Actual Nginx document roots, log paths, and independently verifiable deployed SHA for each environment.
- Rollback process supported by the real deployment scripts.

When evidence conflicts, verify actual host configuration rather than treating an old setup guide as current reality.
