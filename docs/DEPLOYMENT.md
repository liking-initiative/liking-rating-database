# Deployment Guide

The app deploys to [Render](https://render.com) from [render.yaml](../render.yaml):

- **liking-rating-api** — Python web service running
  `uvicorn backend.app:app`. The build step runs
  `scripts/setup_database.py`, which extracts the SQLite database shipped in
  the repo (`data-release/liking_rating_db.db.gz`, 86 MB) into `./data/` —
  deploys are fully self-contained, no external hosting involved.
- **liking-rating-frontend** — static site built from `frontend/` with an SPA
  rewrite so React Router deep links work.

## Deploying

1. Push to GitHub.
2. In the Render dashboard: **New → Blueprint**, select the repo. Render reads
   `render.yaml` and creates both services.
3. Verify: `https://<api>.onrender.com/health` returns
   `{"status": "healthy"}`, and the frontend loads studies.

Environment is configured in `render.yaml` (`DATABASE_URL`, CORS origins,
trusted hosts, log level). The API is read-only, so no secrets are required.

## Known limitations (accepted for now)

- **SQLite on ephemeral disk.** Render's free tier has no persistent disk;
  the database is re-extracted on every deploy. That is acceptable because
  the API is read-only — the only runtime writes are download/search logs,
  which are disposable. `setup_database.py` validates the extracted database
  (tables, non-zero ratings) and **fails the build loudly** rather than
  falling back to an empty database.
- **Download files live in the OS temp dir** and disappear on restart;
  links expire after 24h anyway, and an hourly cleanup task prunes them.
- **In-process rate limiting** (per-IP sliding window, honors
  `X-Forwarded-For` behind Render's proxy). Good enough for a single
  instance; would need a shared store if scaled out.

## Upgrading the database file

The database is versioned by the migrations recorded inside it
(`schema_migrations` table) and ships in the repo. To release new data:
apply the migration locally, regenerate `data-release/liking_rating_db.db.gz`
(checkpoint WAL → `.backup` → `gzip -9`; exact commands in
[DEVELOPMENT.md](DEVELOPMENT.md)), run the test suite, commit, push. The next
deploy picks it up automatically — git history is the data version history.

## Longer-term: PostgreSQL

If the project outgrows SQLite-on-ephemeral-disk (write features, multiple
instances), the models are plain SQLAlchemy and `config.py` already accepts a
`postgresql+asyncpg://` `DATABASE_URL`; the work is provisioning Postgres,
bulk-loading the data, and re-pointing `DATABASE_URL`. No such migration
script exists yet.
