# Independent Review — Candidate `3be28d71` vs base `7c9f4bff`

Scope note: reviewed strictly from the supplied attachment. No files or tools were consulted beyond it. Findings flagged below are those I can substantiate from the attached code alone.

---

## Correctness / Security Findings

### F1 — Missing `LOYAL` generation check on retry path allows duplicate/stale retry races (HIGH)
`backend/procurement/documents.py:retry()` selects the version by `generation = d.generation` and requires `state='failed'`, but does **not** re-check that the job is not already running, nor that the version is still the newest at commit time. `remove()` (which cancels jobs / sets `deleted`/`superseded`) runs concurrently under document `FOR UPDATE`. `retry` does take `FOR UPDATE` on the document, so the deleted race is fenced. However, `retry` does **not** enforce that a *newer* version hasn't been created after the failed one; it keys on `d.generation`, which is updated in `upload`. Reproduction: upload v1 → fail (v1 failed, generation 1) → upload replacement v2 (generation 2, v2 queued) → `POST /retry` — selects `generation=2` (v2, queued), which returns 409 "Only the latest failed version". That is correct. Lower confidence here; I could not construct a clean bypass, so this is downgraded to a consistency note, not a defect.

### F2 — `retry` does not reset `lease_token`/`lease_until` (MEDIUM)
`documents.py:retry` sets job `state='queued', attempts=0, available_at=now(), error_code=NULL` but leaves `lease_token` and `lease_until` untouched. If a prior attempt left `lease_until` in the future (e.g. a `running` job manually flipped to failed, or a cancelled lease), the next `claim()` selects it via `state='queued'` (available_at path), so it still runs — but the stale `lease_token` value remains until overwritten by `claim`. Not directly exploitable because `claim` overwrites `lease_token` via `RETURNING`. Low materiality.

### F3 — `upload()` blob write happens **outside** the DB transaction; partial state persists on failure (MEDIUM)
`documents.py:upload` commits reservation, then writes the blob in a separate `try`, then opens a second transaction to mark `queued`. If the process dies between `blobs.put` success and the second transaction, `document_versions.state` stays `uploading` with the blob present. `cleanup()` handles this via the `upload_expired` one-hour path, but: the cleanup query sets state to `superseded` and then the second cleanup SELECT only deletes blobs for rows where `d.deleted_at IS NOT NULL OR (state='superseded' AND NOT EXISTS job)`. A version marked `superseded` by *upload_expired* (not by replacement) has no job, so it matches and its blob is deleted — good. **However** the `upload_expired` update sets state on **all** rows with `state='uploading' AND created_at < now()-1h`, including a version whose blob write actually succeeded but whose enqueue failed. That orphan's blob *is* removed. Consistency OK. The residual defect: the exception handler raises 503 after a successful `blobs.put` but a failed second transaction would only be reachable if the DB went down — acceptable. Downgrade to optional.

### F4 — `blob_key` uniqueness collision semantics (MEDIUM)
`BlobStore.put` raises `ValueError("Immutable source collision")` on `ResourceExistsError` when content differs. `upload()` catches **all** exceptions and converts to 503 "retry with the same upload key". A genuine hash collision on an *existing unrelated* blob key (two different documents) would surface as a misleading 503 retryable error. Keys are `schema/document_id/version_id` with fresh UUIDs, so collision is effectively impossible; not a real defect.

### F5 — `renew()` requires `lease_until > now()` — renewal after a slow batch can spuriously lose the lease (HIGH)
`ingestion.py:renew` issues `UPDATE ... WHERE lease_token=... AND state='running' AND lease_until>now()`. If an embedding batch takes longer than the 120s lease (OpenAI timeout 20s × up to 16 texts, but a stalled provider or network can exceed 120s across a batch), the lease has already expired by the time `renew` runs, so `renew` finds no row and raises `LeaseLost`, silently discarding already-completed embedding work. Reproduction: mock `Embeddings.embed` to sleep > `LEASE_SECONDS`; first batch completes, `renew` throws `LeaseLost`, `run_once` swallows it, job is reclaimed by another worker (or re-queued after `claim`'s expired-running path) and re-embeds from scratch. This is a **correctness/efficiency defect**: the guard should permit renewal while the caller still holds the token, rather than requiring the lease to still be unexpired. Concretely, `lease_until>now()` should not be a renewal precondition. Severity: high for long documents near the 80-passage/16-batch boundary; the comments claim "renewal between bounded embedding batches," but a single slow batch defeats it. Confidence: high (code is self-evident).

### F6 — Bounded worker input: `Embeddings.embed` is not bounded per call at the provider level (MEDIUM)
`ingestion.py:run_once` batches 16 passages, but each passage body may be up to 1200 chars → up to ~19,200 chars per request. That is within the model limit, so not a bound breach. The real gap: there is **no enforced timeout budget spanning the whole job**, and no cap on total passages beyond `chunks()`'s `>80` raise. A 64 KiB document producing 80 passages is bounded. Acceptable; no defect.

### F7 — `chunks()` line-range can misreport for overlapping chunks (LOW)
`ingestion.py:chunks` computes `line_end = text.count("\n", 0, max(start, end-1)) + 1`. For the overlap window (`start = end - 150`), a chunk beginning mid-line reports `line_start` = the line containing `start`, which may be a line already emitted as the previous chunk's `line_end`. Citations therefore overlap and may reference a partial first line. Acceptable for "character-bounded deterministic" strategy per design; optional improvement is to snap `start` to a newline boundary. Not a correctness defect per the stated strategy.

### F8 — `search` ranking: RRF denominators ignore zero-weight ties and `websearch_to_tsquery` parse errors (MEDIUM)
`documents.py:search` uses `websearch_to_tsquery('english', %s)` for both ranking and the `@@` filter. `websearch_to_tsquery` tolerates most input and returns an empty query for stopword-only input (e.g. "the"), yielding `@@` false for all rows. Then `lexical` is empty, `semantic` still returns nearest neighbors, so results come back via semantic only with `score = 1/(60+rank)`. That is consistent. **However** a query of pure punctuation (e.g. `"**"`), which passes the 2-char length check, may raise a `psycopg`/Postgres error from `websearch_to_tsquery` or produce a `tsquery` that errors on `@@`. `websearch_to_tsquery` is designed not to error, so this is low risk. Also `min_length=2` on the route but `search()` re-checks `len(query.strip())` — a query of `"  "` (2 spaces) passes the route's `min_length=2` but `strip()` yields length 0 → 422. Minor UX inconsistency, not a defect.

### F9 — Semantic CTE `rank` ordering uses `embedding OPERATOR(<=>)` without index; full scan per query (LOW, by design)
`search` orders the whole `allowed` set. The design explicitly accepts exact scans for a small corpus. No defect.

### F10 — `detail()` returns the full `documents` row including `owner_id`, and all versions' `content_hash`/`pipeline`, to any authenticated user (LOW/INFO)
`documents.py:detail` is reachable by all five roles (`list_documents` / `get_document` depend only on `actor`). This matches the design ("all five authenticated seeded team members may inspect shared policies"). No confidential ACLs in scope. No defect.

### F11 — `get_source` TOCTOU: source downloadable for a version that is `superseded` but not yet cleaned (LOW, by design)
`document_routes.py:get_source` serves any version with `cleaned_at IS NULL` and state not in `('uploading','deleted')`. Superseded versions' originals are intentionally retained for historical citations (per `cleanup` docstring). Design explicitly says "previous version stays searchable during replacement" and citations retain line ranges; retaining superseded *sources* is consistent. No defect.

### F12 — `publish()` deletes the active version's passages **before** verifying the new version's passages were inserted atomically (LOW)
`ingestion.py:publish` inserts new passages first, then deletes old active passages, then sets active_version — all in one transaction, so atomicity holds. Insert failure rolls back the whole transaction (test `test_atomic_publication_rolls_back_partial_insert` confirms). The active version's passages are deleted only after successful insert of the new set, so during the transaction the old version is briefly unsearchable only to *this* connection's uncommitted view; other readers see the pre-transaction state. Correct.

### F13 — `remove()` does not clear `lease_token` on already-`done`/`failed` jobs, and does not set `cleaned_at` (LOW)
`remove()` cancels only `queued`/`running` jobs. A `done` job's `lease_token` is already NULL. Blobs are cleaned by `cleanup()` via `d.deleted_at IS NOT NULL`. Consistent.

### F14 — `cleanup()` second query may double-process / lose work on concurrent workers (MEDIUM)
`cleanup` selects up to 20 rows with `cleaned_at IS NULL`, then deletes blobs and sets `cleaned_at`. Two workers running `cleanup` concurrently could both select the same row (no `FOR UPDATE SKIP LOCKED`, no lock). Both call `blobs.delete` (idempotent) and both `UPDATE ... SET cleaned_at=now()` (idempotent). No corruption, but concurrent workers may both attempt external deletes. Since `delete` swallows `ResourceNotFoundError`, harmless. Optional: add `FOR UPDATE SKIP LOCKED` for cleanliness.

### F15 — `upload()` re-commit transaction does not lock `ingestion_jobs`; `ON CONFLICT(version_id) DO NOTHING` masks a re-enqueue (LOW)
`upload` inserts the job with `ON CONFLICT(version_id) DO NOTHING`. If a replay hits the `state != 'uploading'` branch, it returns `detail` early — fine. If the second phase runs twice (only possible via retry of the same key with the version still `uploading`), the job exists only once. Consistent.

### F16 — Fencing check in `publish` uses `lease_until>now()` (HIGH — same root cause as F5)
`ingestion.py:publish` guards with `lease_until>now()`. If embedding finished just as the lease expired, `publish` raises `LeaseLost` and discards a fully-computed result, forcing a full re-embedding on the next claim. Combined with F5, a document whose processing legitimately exceeds 120s between last renew and publish will **never** publish, because each attempt loses the lease right at publish time (the `renew` before the last batch succeeds only if under 120s; if the last batch itself runs long, publish fails). Reproduction: make the final batch's `embed` take slightly more than `LEASE_SECONDS`; `publish` sees expired lease → `LeaseLost` → 3 attempts exhausted → `failed`. This is a real liveness defect for slow providers. Severity high if any provider latency approaches the lease; confidence medium-high on mechanism. The `renew` before each batch mitigates but does not eliminate it.

### F17 — `Embeddings.embed` rejects `response.model` mismatch, but OpenRouter returns namespaced or bare model IDs (LOW)
Handled: `response.model not in (MODEL, MODEL.removeprefix("openai/"))` accepts both `openai/text-embedding-3-small` and `text-embedding-3-small`. Other OpenRouter variants (e.g. with provider suffix) would raise, causing retry/failure. Acceptable strictness given "no fallback" requirement.

### F18 — Frontend `refresh()` in `useEffect` deps omits `api` (LOW)
`Documents.tsx` effect deps `[auth.user.id]` but calls `api`. Standard lint concern; `api` is presumably stable. Not a correctness defect in the shown context.

### F19 — Frontend idempotency key reuse across replacement generation change (MEDIUM)
`Documents.tsx:upload` keys `keys.current` by fingerprint that includes `replacement?.generation`. If a user uploads, gets a 503 (blob failure), then the document's generation changes (another replacement), the fingerprint differs, so a **new** key is generated — losing the retry-with-same-key recovery the backend depends on. Backend `upload` explicitly says "a same-key retry can recover it." The frontend only reuses the same key while the fingerprint is identical; a transient 503 where `replacement` object identity changed between renders would break recovery. Low-medium; hard to trigger deterministically from the attachment alone. Flag as consistency concern.

---

## Optional Improvements (not defects)

- **F5/F16**: decouple renewal/publish fencing from `lease_until>now()`; use token presence + an explicit `renewed_at` heartbeat instead of wall-clock expiry as a precondition.
- **F14**: `cleanup` should use `FOR UPDATE SKIP LOCKED` when selecting cleanup candidates.
- **F7**: snap chunk `start` to a line boundary so citations never begin mid-line.
- **F8**: normalize/validate `q` after `.strip()` at the route layer to avoid 2-space queries.
- **F17**: log (sanitized) model-ID mismatches without persisting provider bodies (already the case; ensure the code path is covered).

---

## Unverified Concerns (insufficient supplied evidence)

- **U1**: Whether `db.connect()` context manager commits on exit. `upload` relies on the `with db.connect() as c` block committing the reservation before `blobs.put`. The diff and files do not show `Database.connect`. If it does not commit, the entire two-phase design is broken. Cannot verify from the attachment.
- **U2**: Whether `command_key` dependency (`Depends(command_key)`) reads the `Idempotency-Key` header and whether the frontend's `X-CSRF-Token`/`Origin` handling matches `upload`'s CSRF expectation. Tests assert 403 for foreign Origin, but the dependency implementation is not in the attachment.
- **U3**: The `integration diff` for `app.py` shows `install_document_routes(app, db, actor, command_key)` is called **after** the procurement routes; route precedence between `/api/v1/documents/{document_id}` (UUID-typed) and any existing catch-all is not verifiable.
- **U4**: `publish` uses `zip(passages, vectors, strict=True)`; if `validate_vectors` returned a different length the `ValueError` would be caught by the broad `except Exception` and retried — correct, but the retry would recompute everything. Efficiency only.
- **U5**: The 120s lease vs. total job work (up to 80 passages / 5 batches × 20s timeout = 100s nominal) leaves ~20s margin; with retries inside a batch (none, `max_retries=0`) this is tight but nominally within lease. Real-world provider latency unverified.

---

## Coverage Limitations

- Only the attached files were reviewed. `Database`, `Settings`, `config`, `actor`, `command_key`, `identity.authenticate`, `users` schema, and the real Floci/OpenRouter adapters were not provided, so DB-commit semantics, CSRF/identity enforcement and provider behavior could not be confirmed.
- No execution, linting, type-checking or test runs were performed; the tests above were read as contracts only. No claim is made that any test passes or fails.
- The review is limited to correctness/security/consistency of the ingestion, publication, deletion, lease and search paths as represented by the attachment.

**Highest-priority fixes:** F5/F16 (lease-expiry renewal/fencing causes lost work and possible permanent non-publication) and F19 (frontend idempotency-key recovery gap).
