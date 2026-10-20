# EdgeLog environment reference (non-secret)

Updated: 2026-10-20. This is an operational reference, NOT an application .env file. Never put passwords, tokens, database URLs, or API keys here.

## Known
- Repository: https://github.com/khammrich1/edgelog
- DEV URL: https://d.edgelog.trade
- PROD URL: https://edgelog.trade
- Stack: FastAPI / Uvicorn, Vue 3 / Vite, PostgreSQL, Alembic.
- Production deployment guide documents /var/www/edgelog/backend as an example backend path and /var/www/edgelog/frontend for built assets. These are NOT confirmed DEV paths.
- README (2026-10-11) describes a DigitalOcean App Platform migration as a priority; actual current DEV deployment type is NOT verified.
- Repo deployment guide: DEPLOYMENT.md; development guide: DEVELOPMENT.md.
- PR #91 branch: feat/issue-80-reconciliation-preview; observed head on 2026-10-20: b6bae1716b609b9b6168e939fe72b48caaa37d30. Recheck before deploying.

## Needs verification before issuing server commands
- DEV platform: DigitalOcean App Platform vs droplet.
- DEV app/project identifier and deployed git SHA.
- DEV repository checkout directory, if a droplet.
- DEV deployment procedure and rollback procedure.
- PROD platform, checkout directory, and deployment SHA.

## Verification procedure
1. Inspect current DigitalOcean DEV app settings/deployment details or droplet service configuration.
2. Record confirmed paths, app identifiers, and verification date here.
3. Compare DEV deployed SHA with PR head before owner testing.
4. Do not assume a path from production docs is the DEV checkout.
5. Do not store secrets here. Keep runtime .env files untracked.
