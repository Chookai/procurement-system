# Local runtime compatibility

Verified 23 October 2026. Scope: reproducible dependencies and integration contracts. This is not an implemented procurement backend, a real retrieval evaluation, or a production-readiness result.

## Locked baseline

| Component | Verified version |
|---|---|
| Python | 3.12.3 |
| uv | 0.11.15 |
| Docker Engine / Compose | 29.1.3 / 2.40.3 |
| Microsoft Agent Framework OpenAI adapter / core | 1.17.0 / 1.23.0 |
| Compatible API SDK | openai 3.37.0 |
| FastAPI / Uvicorn | 0.161.1 / 0.54.0 |
| Azure Blob Python SDK | 12.31.0 |
| psycopg | 3.3.6 |
| PostgreSQL / pgvector | 17.11 / 0.8.7 |
| Floci AZ | 0.15.0 |

Direct dependencies are declared in `backend/pyproject.toml`; all transitive versions and package hashes are in `backend/uv.lock`. `infra/compose.yaml` pins both container image digests. Existing user containers were left untouched: the new project uses localhost ports 15432 and 14577 and separate named volumes. No Docker socket is mounted into Floci because this slice only requires Blob operations.

We run PostgreSQL directly using the pgvector image rather than Floci's default PostgreSQL sidecar. This supplies the selected extension explicitly while retaining Floci for Blob SDK compatibility. It does not introduce another application service or external queue.

## Checks and evidence

| Check | Result | Evidence |
|---|---|---|
| PostgreSQL full text and vector query | Passed against the real database | `runtime-results/local-exercise.json` |
| Concurrent `FOR UPDATE SKIP LOCKED` sessions | Passed; second session skipped the locked fixture | Same report; this verifies a lease primitive, not a worker |
| Blob operations | Container creation, upload, metadata, properties, list, download, range, overwrite and deletion passed through Azure SDK | Same report |
| Graceful restart persistence | Both the database row and Blob bytes survived Compose restart | `runtime-results/local-seed.json`, `local-verify.json` |
| FastAPI dependency compatibility | In-process health route/TestClient passed | `runtime-results/local-exercise.json`; no real application route yet |
| Live model integration | Chat, streaming, read-only function execution, structured output and embeddings passed | `runtime-results/provider-live.json` |
| Simulated provider failures | 401, 429, 500 and read timeout propagated as errors; no success answer or hidden retry loop | Four pytest cases; `runtime-results/provider-failures.xml` |

Provider checks use synthetic prompts, not indexed procurement documents. Persistence was checked across graceful restart, not crash recovery or backup/restore. The lease check does not verify retry policies, job completion or idempotency of an ingestion worker.

## Initial provider configuration

- Generation route: `openai/gpt-4.1-mini`, through OpenRouter Chat Completions and Microsoft Agent Framework `OpenAIChatCompletionClient`.
- Embedding route: `openai/text-embedding-3-small`, 1,536 dimensions, through a direct SDK embedding call to OpenRouter.
- Restrict provider to `openai`, disable fallbacks, require parameter support. The live probe inspects outgoing bodies to verify these options reached every request.
- Live nonstreaming responses reported provider `OpenAI`. The report stores actual model fields, response IDs and usage/cost when returned. Streaming verifies incremental output; the probe does not capture its full provider/cost metadata yet.
- These route IDs are initial integration baselines, not immutable weight snapshots or quality-certified release selections. Resolve and record the exact available model identity/routing again before freezing a release evaluation. Neither a passing contract nor the public model capability list establishes procurement answer quality.
- SDK retries are disabled in the probes; explicit bounded application retries and error-to-HTTP behavior belong to the backend implementation.
- Keep secrets in ignored `backend/.env` or server environment variables. They are not serialized into reports or sent to the frontend. No Foundry SDK, credentials or deployment is required.

The framework embedding client does not pass through OpenRouter routing options in the verified version. Using the direct embedding SDK adapter preserves route restrictions. Generation continues through Microsoft Agent Framework; embedding and generation remain separately configured.

## What remains before milestone completion

Build the API, identity and workflow persistence; actual document ingestion/worker; permission-filtered retrieval and source inspection; reproducible corpus and holdout; real RAG runs and calibrated gates; operational behavior; and the user code walkthrough. Current results establish only the runtime contracts above.

## Primary sources reviewed

- [Floci AZ 0.15.0 release](https://github.com/floci-io/floci-az/releases/tag/0.15.0): selected release; required SDK operations were tested locally rather than inferred from the feature list.
- [pgvector repository](https://github.com/pgvector/pgvector): extension/image and query interfaces.
- [Microsoft Agent Framework compatible-client package](https://github.com/microsoft/agent-framework/blob/main/python/packages/openai/README.md): distinct Chat Completions and Responses clients; the installed pinned source was also inspected.
- [OpenRouter API reference](https://openrouter.ai/docs/api_reference/overview): compatible schema, streaming, tools and structured-output options. Actual route support was tested.
- [OpenRouter generation model catalogue](https://openrouter.ai/api/v1/models) and [embedding catalogue](https://openrouter.ai/api/v1/embeddings/models): initial route discovery; live calls supplied the integration evidence.
