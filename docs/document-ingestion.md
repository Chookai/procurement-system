# Text policy ingestion and retrieval

Implemented slice for [issue #18](https://github.com/Chookai/procurement-system/issues/18), under the broader ingestion ticket #12. Design and boundaries: [document-ingestion-design.md](document-ingestion-design.md).

## Run locally

Use the locked backend environment, existing ignored `backend/.env` and Node setup. These commands run in separate terminals from the repository root:

```bash
docker compose -f infra/compose.yaml up -d postgres blob
uv sync --project backend --locked --python 3.12.3
uv run --project backend --locked uvicorn procurement.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8001
# Separate terminal: the API never processes ingestion jobs in its request thread.
cd backend
uv run --locked python -m procurement.ingestion
# Separate terminal, repository root:
npm run app
```

One-shot worker, from `backend/`: `uv run --locked python -m procurement.ingestion --once`. A worker startup applies pending migrations; it does not seed users itself. Start the API first.

`BLOB_ENDPOINT` defaults to the existing loopback Floci service. The adapter deliberately rejects non-loopback Blob endpoints; real Azure authentication is later work. Server-side `OPENROUTER_API_KEY` is needed for real embeddings, not for HTTP contract tests. No key goes in the frontend. The fixed embedding manifest uses `openai/text-embedding-3-small`, 1536 dimensions, `openai` provider only, fallback disabled. Environment model settings in `.env.example` remain compatibility-probe inputs; they do not silently change the ingestion manifest.

## Try the journey

1. Open the app at http://127.0.0.1:5175/?view=documents&theme=dark. Sign in as `chloe`, seeded password `harbor-demo`.
2. Open **Policy documents**, enter a title and upload one file from `fixtures/policies/`. Maximum source size is 64 KiB; supported encodings/formats are UTF-8 `.txt` and `.md`.
3. Status moves from waiting to processing to searchable as the separate worker runs. The screen polls every four seconds. A missing worker leaves the job queued; it is not a successful ingestion.
4. Search “Does invoice review authorize payment?” Inspect the passage, version, line range and downloadable original source. This is hybrid evidence retrieval, not generated answering.
5. Replace the source. The old published version remains searchable until the replacement is complete. History retains source identifiers/hashes.
6. Only Chloe can retry a latest failed job or confirm deletion. Deletion immediately removes evidence from retrieval/downloads; physical Blob deletion is retried by cleanup. An incomplete upload expires after an hour and requires a new replacement upload.
7. Sign in as another seeded role to inspect/search; upload/replacement/retry/deletion controls are unavailable and unauthorized API writes return 403.

All five users share this single synthetic policy corpus. It does not store restricted PR attachments or establish tenant isolation. Markdown is rendered as escaped plain text.

## Module map

| File | Responsibility |
|---|---|
| `frontend/src/Documents.tsx` | Library, upload/replacement, status, search and source inspection |
| `backend/procurement/document_routes.py` | HTTP authentication/CSRF dependencies and bounded raw file transfer |
| `backend/procurement/documents.py` | Buyer authorization, idempotency, versions, deletion and hybrid retrieval |
| `backend/procurement/document_adapters.py` | Local Floci I/O and bounded OpenRouter embedding calls |
| `backend/procurement/ingestion.py` | Deterministic chunks, durable claims/leases, atomic publication, retry and cleanup |
| `backend/migrations/006_documents.sql` | Source metadata, jobs, passages/vectors and ingestion audit events |

Source and passage IDs are stable UUIDs. Original bytes are hashed; line citations refer to normalized UTF-8 text. Pipeline identity includes the chunking strategy, embedding route, dimension and provider. Model routes are not immutable weight snapshots. Corpus/model changes need fresh retrieval evaluations before release claims.

## HTTP contracts

All endpoints require the existing session; state-changing calls require CSRF. Upload endpoints also require `Idempotency-Key`. Upload bodies are raw source bytes, not JSON or multipart.

| Method / path under `/api/v1` | Purpose |
|---|---|
| `GET /documents` | Latest 100 live documents with source history; pagination is future work |
| `POST /documents?filename=policy.md&title=Team%20policy` | Reserve/store a source and enqueue its job; returns 202 |
| `POST /documents/{id}/versions?filename=policy.md&title=Team%20policy&expected_generation=1` | Optimistically replace source, returns 202 |
| `GET /documents/{id}` | Inspect generations and current searchable pointer |
| `GET /documents/search?q=invoice` | Current published passages, hybrid reciprocal-rank fusion, up to five results |
| `GET /documents/{id}/versions/{version}/source` | Authorized original text download |
| `POST /documents/{id}/retry` | Buyer retries latest terminal failure; maximum three attempts per retry cycle |
| `DELETE /documents/{id}?expected_generation=1` | Buyer tombstones current document; returns 204 |

Storage/provider errors are sanitized and fail explicitly. There is no silent embedding fallback or simulated-success answer. A source is durably reserved before Blob transfer; source readiness and job insertion commit together. Publication holds the document lock and checks the current generation and unexpired lease token before committing passages, active pointer and job completion atomically. Search uses only that pointer with a matching pipeline. Old passage rows are removed on publication, while old source bytes remain available until document deletion.

## Evidence and limits

Run credential-free tests with real PostgreSQL:

```bash
uv run --project backend --locked python -m pytest backend/tests -q
npm run app:check
npm run app:build
```

The local full suite passed 91 cases (75 existing + 16 new cases) before final documentation changes. The new test module uses deterministic injected external adapters; it is not paid model coverage. It exercises authorization/CSRF, invalid sources, upload replay/conflicts/storage failure, publication/replacement/deletion, retry limits, manual retry, unique concurrent claims, expired/stale leases, rollback and cleanup.

Paid synthetic live probe, from the repository root:

```bash
uv run --project backend --locked python tools/runtime/check_ingestion.py
```

This uses an isolated schema and unique Blob prefix, and cleans only its own sources/schema. It stores sanitized evidence in `runtime-results/document-ingestion-live.json`. Three labelled development questions retrieved the expected source at rank one and downloaded matching original bytes. These examples are deliberately tiny, not a representative retrieval benchmark, frozen holdout or answer evaluator. Reported embedding usage in the record is the last query response, not aggregate cost.

The local browser script `tools/check-documents.cjs` follows upload, publication, search, replacement, deletion and read-only reviewer behavior with separate Chromium. It checks light/dark and 390px layout, and saves `runtime-results/document-ingestion-browser.json`. Its local installed-Chrome dependency is explicit; Kilo's portable CI browser task is separate and this script is not added to hosted CI. Existing backend CI automatically discovers the credential-free ingestion tests; no workflow change is required for them.

No PDF/OCR, agent tools/answers, full RAG eval runner, dedicated rate limits, tracing pipeline, production identity, confidential documents, real Azure contracts or deployment is implemented here. The current upload size, exact vector scans and bounded corpus list suit the small local milestone. User review and broader ticket/milestone acceptance remain outstanding.

## Final GPT review before merge

The final code candidate `994d516a` adds recovery for a crash between a final job claim and marking the version processing, plus shared source-write/cleanup fencing. Logical deletion remains independent of external source I/O. The new regression cases cover normal late-upload rejection and simulated process death immediately after Blob write.

Fresh local results on disposable PostgreSQL: **100 backend tests passed**; independent GPT follow-up ran **25 document tests, all passed**. Three newly added cases fail against the prior `077b8eb8` snapshot and pass on the fix. These are fake-adapter tests, not paid-provider or Azure verification. [Final review evidence](verification/final-gpt-premerge-review.md) records the tested snapshots, commands, limits and merge authorization. Latest hosted status and final merge commit are recorded on PR #20.
