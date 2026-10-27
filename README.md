# Procurement learning project

A fictional marine procurement application and RAG learning workspace. The first real application slice now supports five seeded logins and durable PR creation, submission, return-for-change and approval. PO issuance/reapproval, partial goods receipts and service acceptance are also implemented; supplier invoice capture/review is also implemented. Ingestion, agent tools/retrieval and the RAG evaluation runner remain to build. See the [invoice walkthrough](docs/invoice-slice.md) and [lesson 06](learnings/lessons/0006-review-is-not-payment.html). See the [receiving walkthrough](docs/receiving-slice.md) and [lesson 05](learnings/lessons/0005-receipts-and-revisions.html). See the [revision walkthrough](docs/po-revision-slice.md) and [lesson 04](learnings/lessons/0004-approval-is-not-issuance.html). The clickable prototype and learning pages are separate artifacts. Microsoft Foundry is deferred.

## Run the application

Start dependencies with `docker compose -f infra/compose.yaml up -d --wait`, then use two terminals from the project root:

```bash
# Backend (WSL/Linux)
uv sync --project backend --locked
uv run --project backend --locked uvicorn procurement.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8001
```

```bash
# Frontend (using the available Node/npm toolchain)
npm ci --prefix frontend
npm run app
```

Open http://127.0.0.1:5175/?theme=dark. Demo usernames: `aina`, `ben`, `chloe`, `dinesh`, `eva`; local demo password: `harbor-demo`. The API uses persistent PostgreSQL; it does not reset with the browser. The Vite server proxies `/api` to port 8001.

Read the [first-slice walkthrough and API contract](docs/first-application-slice.md) before inspecting the code. API docs: http://127.0.0.1:8001/docs.

See the [PO issuance walkthrough](docs/purchase-order-slice.md) and [Lesson 03](learnings/lessons/0003-purchase-order-snapshots.html) for the next extension.

## Inspect the current work

- [Approved milestone specification](.scratch/procurement-mvp/spec.md)
- [Definition of done](docs/milestone-1-definition-of-done.md)
- [Runtime compatibility evidence and limits](docs/runtime-compatibility.md)
- [Architecture direction](docs/architecture-direction.md)
- [RAG learning workspace](learnings/README.md)
- [Canonical RAG evaluation plan](learnings/rag-evaluation-plan.md)

## Start the verified local dependencies

Run these commands from the project root in WSL/Linux. Tested with Python 3.12.3, uv 0.11.15 and Docker Compose 2.40.3.

```bash
uv sync --project backend --locked
# Isolated loopback services: PostgreSQL :15432, Floci Blob :14577.
docker compose -f infra/compose.yaml up -d --wait
uv run --project backend --locked python tools/runtime/check_local.py
uv run --project backend --locked python -m pytest backend/tests -q
```

These commands start/check dependencies, not a procurement API. The virtual environment is created under `backend/.venv`; the recorded checks used the same lock in an isolated temporary environment. Docker volumes retain local data. Public development database credentials in Compose are only for this loopback setup.

To verify graceful restart persistence:

```bash
uv run --project backend --locked python tools/runtime/check_local.py --mode seed
docker compose -f infra/compose.yaml restart
# Wait until services are healthy before verifying.
docker compose -f infra/compose.yaml up -d --wait
uv run --project backend --locked python tools/runtime/check_local.py --mode verify
```

To stop these project services without deleting their data:

```bash
docker compose -f infra/compose.yaml stop
```

## Real model contract checks

Copy `backend/.env.example` to `backend/.env` only if that file does not already exist, then set `OPENROUTER_API_KEY` there. Never put a key in source files, reports or browser code. Existing values must not be overwritten by setup commands.

```bash
uv run --project backend --locked python tools/runtime/check_provider.py
```

This makes small paid model calls with synthetic prompts and writes sanitized results under `runtime-results/`. Missing credentials exit nonzero as pending. These are compatibility probes, not quality evaluations; the real corpus/holdout runner remains pending.

## Design and learning pages

```bash
python3 tools/build-learnings.py
python3 tools/build-ticket-register.py
npm run prototype
```

The prototype dependencies must already be installed in `mockups/procurement-ui-prototype`; otherwise run `npm ci --prefix mockups/procurement-ui-prototype` first.

- Prototype: http://127.0.0.1:5173/prototype/procurement?variant=C&theme=dark
- Read-only tickets: http://127.0.0.1:5173/tickets.html?theme=dark
- Learning hub: http://127.0.0.1:5173/learnings/index.html?theme=dark

Variant C in the example URL is a preview, not a recorded final layout selection. These pages are design/teaching artifacts, with mocked procurement and assistant behavior.

## Check the first application slice

```bash
uv run --project backend --locked python -m pytest backend/tests -q
npm run app:check
npm run app:build
```

Backend tests use temporary database schemas; the application records remain in the separate `procurement` schema. See [first-slice verification](docs/first-application-slice.md#verification) for the browser and restart evidence.

## Version control and CI

Local Git history starts with the current implementation as a baseline. GitHub Actions is prepared in [.github/workflows/ci.yml](.github/workflows/ci.yml) for frontend/docs and PostgreSQL-backed backend checks. No remote is configured yet, so a hosted run remains pending. See the [interactive plan](learnings/reference/git-ci-cd-plan.html) and [execution details](docs/git-ci-cd.md). Azure deployment follows after infrastructure and release prerequisites are configured.

## Development-agent handoff

Planning/specs/tickets stay here with the orchestrator; Kilo Desktop with a cheaper model implements; verification returns here against a fixed candidate commit. See the [HTML workflow report](learnings/reference/agent-workflow-report.html) and [handoff contract](docs/development-agent-workflow.md). Kilo setup and automatic dispatch are not configured yet.
