# Portable browser smoke suite

The browser smoke suite is a reproducible [Playwright](https://playwright.dev/)
test that drives the real React frontend and the real FastAPI backend through
one core procurement journey. It runs locally and in the `browser-smoke` CI job
without OpenRouter or Azure credentials.

## What it covers

`frontend/e2e/smoke.spec.ts` exercises:

1. Aina (seeded requester) signs in.
2. She creates a uniquely titled purchase requisition and saves it.
3. She refreshes the page and confirms the saved record persists.
4. She submits it for approval.
5. Ben (seeded approver) signs in, selects that PR and approves it.
6. The approved state and the expected next action are visible.
7. Aina cannot see an approval action for her own request.

Backend authorization remains authoritative: step 7 only asserts that the
approval control is not offered to the requester. The API still rejects a
self-approval regardless of what the UI shows.

## Isolation

- The suite never connects to the user's procurement database. The backend is
  started with `DATABASE_URL` taken from `SMOKE_DATABASE_URL`, which must point
  at a **disposable test database**. The local default is a throwaway database
  on port `15433`; CI runs its own PostgreSQL service with the
  `smoke_procurement` database.
- The backend migrates and seeds its five seeded users on startup, so the suite
  works on an **empty** database. It does not depend on existing PR numbers,
  manual preparation or historical records.
- The frontend and backend run on disposable ports (`SMOKE_FRONTEND_PORT`,
  default `5275`; `SMOKE_BACKEND_PORT`, default `8101`) so the suite never
  attaches to a running app instance.
- Identities are the synthetic seeded users (`aina`, `ben`, `chloe`, `dinesh`,
  `eva`) with the local demo password. No real credentials are read or stored.
- Each run uses a unique request title, so repeated runs do not collide.

## Prerequisites

- Node from `.nvmrc` (24.13.0) and npm.
- `uv` (0.11.15 in CI) for the locked backend environment.
- A disposable PostgreSQL 17 with pgvector. Locally, start one with:

  ```bash
  docker compose -f infra/compose.yaml up -d postgres   # app database (port 15432)
  ```

  For the smoke suite, point `SMOKE_DATABASE_URL` at any disposable database.
  A quick throwaway instance on port 15433:

  ```bash
  docker run --rm -d --name procurement-smoke-pg \
    -e POSTGRES_USER=procurement \
    -e POSTGRES_PASSWORD=procurement-local-only \
    -e POSTGRES_DB=smoke_procurement \
    -p 127.0.0.1:15433:5432 \
    pgvector/pgvector:0.8.7-pg17
  ```

  Never point `SMOKE_DATABASE_URL` at your real procurement database.

## Run locally

```bash
npm ci --prefix frontend
npm run smoke:install          # installs Playwright's bundled Chromium
uv sync --project backend --locked --python 3.12.3

export SMOKE_DATABASE_URL="postgresql://procurement:procurement-local-only@127.0.0.1:15433/smoke_procurement"
npm run smoke
```

Playwright starts the backend (`uvicorn` on the smoke port) and the frontend
(`vite` on the smoke port) automatically, waits for both readiness probes, runs
the test, and shuts them down. Set `SMOKE_FRONTEND_PORT` / `SMOKE_BACKEND_PORT`
to override the ports.

On Windows PowerShell:

```powershell
$env:SMOKE_DATABASE_URL = "postgresql://procurement:procurement-local-only@127.0.0.1:15433/smoke_procurement"
npm run smoke
```

## Failure evidence

- HTML report: `frontend/playwright-report/` (`npx --prefix frontend playwright show-report`)
- Trace, screenshot and video for failures: `frontend/test-results/`
- The trace is captured on the first retry; screenshots and video are kept on
  failure. In CI (`retries: 1`) these are uploaded as the `browser-smoke-report`
  artifact, and the artifact step runs `if: failure()`.

All generated outputs (`playwright-report/`, `test-results/`) are ignored by
Git.

## Timeouts

Startup and test timeouts are bounded in `frontend/playwright.config.ts`:
60 s per test, 15 s per assertion, 120 s for each service readiness probe. The
suite uses Playwright's built-in readiness/visibility waits and explicit role
and label locators instead of fixed sleeps.

## CI job

`.github/workflows/ci.yml` adds a `browser-smoke` job alongside the existing
`frontend-and-docs` and `backend` jobs:

- PostgreSQL 17 + pgvector service with the `smoke_procurement` database.
- Locked npm and uv installs; Playwright Chromium via `playwright install --with-deps chromium`.
- No OpenRouter/Azure credentials; the suite makes no paid model calls.
- Failure artifacts (`browser-smoke-report`) retained for 14 days.

The suite uses Playwright's bundled Chromium (`npm run smoke:install`), not a
locally installed Chrome and not any absolute machine-specific path.
