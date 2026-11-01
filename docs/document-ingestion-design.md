# Document ingestion: first text slice

28 October 2026. User selected implementation here after design, with Markdown and plain text first. This narrows PROC-011 (#12); it does not complete agent integration or production readiness.

## User journey

Chloe uploads a synthetic team policy (.md/.txt, UTF-8, maximum 64 KiB). All five authenticated seeded team members may inspect shared policies and search their published passages. Only the buyer can upload, replace, retry or delete. This shared policy corpus is explicitly separate from restricted requisition attachments; per-record/confidential document access is not in this slice.

Upload → reserve source version → store original bytes in Floci Blob → commit ingestion job → worker leases job → normalize/chunk → OpenRouter embeddings → atomically publish complete passages in PostgreSQL. React shows processing/failure state and current searchable version.

## Ownership and identity

- Document ID is stable across replacement; source-version ID and content hash identify immutable original evidence.
- Pipeline ID records parser/chunk strategy and exact embedding route/dimensions. Passage IDs are deterministic within a version; citations retain line ranges.
- Existing server identity/CSRF checks apply to document HTTP endpoints. No agent tool is introduced. The open agent-authorization criterion in #6 remains open.
- Markdown is treated as text, never executed or rendered as trusted HTML. Document text cannot authorize actions. Upload endpoints enforce an incremental byte limit and strict UTF-8/extension validation.

## Storage and consistency

Use the accepted Floci Blob adapter, PostgreSQL full-text + pgvector, one separate Python worker and database jobs. Preserve existing dependency versions. Embedding baseline: OpenRouter `openai/text-embedding-3-small`, 1536 dimensions, provider `openai`, no fallback. Query and ingestion must share the same manifest; pipeline changes require reindexing.

Reserve upload metadata before writing the blob, then commit the source state and its job together after a successful write. Reserve each operation under a user/idempotency key and payload fingerprint. Same key/body replays; changed body conflicts. Pending uploads are tracked for bounded cleanup; failed uploads can be retried using the same key. Blob IDs are generated, never derived from filenames. Blob collisions must compare source hash rather than overwrite.

Old published passages stay usable while a replacement processes. Only the newest requested version may publish. Publication, passage replacement and job completion use one transaction. Failed or partially written candidates never enter retrieval. Delete tombstones the document immediately, clears its searchable pointer/passages and invalidates running work; background cleanup removes stored originals. A stale or expired worker lease cannot publish after another claim or deletion.

## Worker and failure controls

Atomic SKIP LOCKED claims; unique version/pipeline jobs; attempt counter; finite leases and fencing tokens; renewal between bounded embedding batches; three attempts with backoff. Crashed final attempts become failed after lease expiry. Manual retry is buyer-only and valid only for the newest failed version. Persist sanitized failure codes, not provider exception bodies. Cleanup processes bounded batches; physical deletion failure remains retryable while logical deletion is immediate.

## Verification

Use real PostgreSQL with isolated schemas and injected Blob/embedding adapters for HTTP, retry, lease, stale-worker, atomicity, replacement/deletion and authorization tests. No paid calls in CI. Separately exercise the real pinned Floci SDK adapter and one small synthetic ingestion/search with the approved OpenRouter credential; report actual evidence and limitations. Add labelled synthetic retrieval cases as development checks, not a frozen holdout or full RAG answer evaluation.

## Deliberate limits

No PDF/OCR, office files, supplier attachments, malware scanner, Entra ID, external queue, Redis, agent answers or Foundry. Character-bounded deterministic chunks are a reproducible initial strategy, not a tuned production tokenizer. Exact vector scans suit this small corpus; add an ANN index only after relevance/latency evaluation. Text ingestion and retrieval do not establish answer quality, Azure parity, tenant isolation or production readiness.
