# Git, CI and later Azure deployment

27 October 2026. User selected GitHub Actions. The interactive review plan is `learnings/reference/git-ci-cd-plan.html` (served from the learning site on port 5173).

## Start version history now

Create one honest baseline commit of the existing PR/PO/GR/invoice implementation, tests, design/prototype sources, canonical learnings, local Markdown tickets, sanitized evidence and delivery foundation. Earlier implementation steps are not reconstructed into invented historical commits. Future work uses short feature branches and focused commits.

Local Git is initialized on `main`, using the existing configured author identity. The user supplied the public repository `Chookai/procurement-system`; `origin` is configured. The first code push currently awaits GitHub workflow permission because the authenticated CLI token was rejected for uploading `.github/workflows/ci.yml`. No force push or history replacement is planned. Once connected, open pull requests and configure required checks for `Frontend and documentation` and `Backend with PostgreSQL`; repository rules are configured on GitHub, not established by the workflow file alone.

Exclude `.env` secrets, generated local signing keys, dependencies, environments, caches and compiled/generated mirrors. Keep `.env.example`, lockfiles, source templates, canonical docs/tickets, and explicitly sanitized verification evidence. Reports retained in `runtime-results/` describe historical checks, not a current GitHub run. New CI reports use ignored `ci-*` paths.

`tools/check-repository.py` checks tracked/staged files for common token patterns, private keys and the actual local OpenRouter/session secrets when available, without printing values. This is a focused guard, not a comprehensive security audit. It checks the Git index, so run it after staging. There are no installed Git hooks in this setup.

## Continuous integration now

Workflow: `.github/workflows/ci.yml`. It runs on pull requests, pushes to main and manual dispatch. GitHub must host the repository before any hosted run can occur.

| Job | Checks | Evidence |
|---|---|---|
| Frontend and documentation | Locked npm installs; React TypeScript check; production app build; regenerate ticket/learnings; validate local teaching links; prototype/teaching-site build; tracked-file hygiene | Frontend build artifact, retained 14 days |
| Backend with PostgreSQL | Python 3.12.3 + uv 0.11.15; locked dependencies; isolated PostgreSQL integration tests and mocked provider failure contracts | JUnit test report, retained 14 days even if tests fail |

Node is pinned to the locally validated 24.13.0 in `.nvmrc`; backend Python remains 3.12.3. Third-party actions use full commit SHAs, and the workflow has read-only repository permissions. The backend service uses the same pinned PostgreSQL/pgvector image as local infrastructure. Its known demo password belongs only to the disposable test database, not a cloud secret.

PR CI requires no OpenRouter/Azure key and makes no paid model calls. It does not invoke `tools/runtime/check_provider.py`. Real-provider RAG evaluation gates will be added with ingestion/retrieval/evaluation, after the development set is calibrated and the holdout protocol is frozen. Current API tests use isolated schemas; they do not touch the user's procurement records.

Browser smoke scripts currently target a running local app and seeded fixtures, with some using installed Chrome. They are retained as manual verification tools and are not presented as hosted CI coverage. A portable browser suite with controlled fixtures can be a later CI job.

### Reproduce the checks locally

```bash
python3 tools/check-repository.py
npm ci --prefix frontend
npm run app:check
npm run app:build
npm ci --prefix mockups/procurement-ui-prototype
python3 tools/build-ticket-register.py
python3 tools/build-learnings.py
python3 tools/check-documentation.py
npm run prototype:build
uv sync --project backend --locked --python 3.12.3
uv run --project backend --locked python -m pytest backend/tests -q --junitxml=runtime-results/ci-backend.xml
```

Use Node from `.nvmrc` and start the PostgreSQL service first (`docker compose -f infra/compose.yaml up -d postgres`). The local environment may use the existing `/tmp/procurement-runtime-venv`; the hosted job creates a clean backend environment. No `.env` is copied into CI. Passing local commands does not prove a hosted Actions run; first-run evidence remains pending until the permission grant and first successful push/run.

## Continuous deployment after deployment readiness

Prepare the deployment design now; create an executable deploy workflow when an actual Azure destination is configured. The application is still a local learning milestone and its in-process agent/RAG journey is not built yet.

Proposed progression:

1. Finish document ingestion, agent/retrieval integration and evaluation gates locally.
2. Define Azure development resources and configuration: frontend hosting choice, Container Apps API/worker, managed PostgreSQL, Blob, secret management and observability. Floci remains a local emulator.
3. Add container packaging, HTTPS/session configuration, migration execution and smoke checks. The current loopback demo session settings are not a deployment configuration.
4. Connect GitHub to Azure with narrowly scoped OIDC federation, avoiding a long-lived Azure deployment password. Configure the actual repository/environment claims when the repository exists.
5. Deploy the tested artifact to a development/staging environment; run smoke and RAG release gates. Promote that tested version through an explicit production environment gate when production requirements and rollback are established.

No deploy workflow, cloud resources, environment approvals, billing resources or Azure identity have been created here. Foundry remains deferred. GitHub CI can be used with Azure hosting; choosing Actions does not select a cloud provider for the application.

## Primary references

- [GitHub checkout action](https://github.com/actions/checkout) and [setup-node](https://github.com/actions/setup-node) — checkout/build tool configuration.
- [Astral setup-uv](https://github.com/astral-sh/setup-uv) — pinned uv/Python and locked environment setup.
- [GitHub upload-artifact](https://github.com/actions/upload-artifact) — build/report artifacts and retention.
- [GitHub OIDC with Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure) — future federated deployment identity; new repository claim formats must be checked when configuring it.

## Local verification · 27 October 2026

The staged source was exported to a clean temporary directory without `.env`, signing keys or dependencies. A checksum-verified official Linux Node 24.13.0 runtime performed both locked npm installs, TypeScript/build checks, document regeneration/link checks and prototype build successfully. A fresh uv environment with Python 3.12.3 ran all 75 backend tests successfully against PostgreSQL without local model credentials. `actionlint` 1.7.12 (release checksum verified) validated the Actions YAML. The review HTML passed theme, print, mobile and browser-error checks. See `runtime-results/git-ci-local.json`; the local ignored JUnit output is `runtime-results/ci-backend.xml`.

This verifies job-equivalent commands locally. GitHub checkout/cache/artifact execution and repository-required-check settings still need a hosted run. The existing ADS dependency tree emits legacy peer/deprecated-theme warnings; the clean installs and builds passed, and npm reported zero vulnerabilities in this run.
