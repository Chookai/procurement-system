# Final GPT premerge review — issue #18 / PR #20

The user explicitly authorized a final GPT review and merge. Two fresh reviewer contexts assessed Standards and Spec against base `7c9f4bff0290db87a52cf5cad1d4f38db7b70057` and prior head `077b8eb87eda134e3de50e383de5e08dc234bed9`.

Both reviewers identified the final-claim recovery defect. The Spec reviewer additionally identified and executed the source cleanup race. Neither finding was inferred from CI failure: the prior head's hosted 97-test CI passed.

## Findings and repairs

| Finding | Before | Fixed code `994d516ae6f3e336e91a518d892f072643a8e9a0` |
| --- | --- | --- |
| P2: crash immediately after final claim | Job becomes failed after lease expiry while version remains queued; buyer retry returns409. | Reconcile exhausted queued and processing versions to failed, preserving deleted/superseded versions. Buyer retry then publishes successfully. |
| P2: source cleanup versus late upload | A deleted source can be recreated after physical deletion, while cleanup marks it complete and skips future passes. Process death after storing bytes exposes the same risk. | Shared per-source advisory transaction fence covers put+final metadata and delete+cleanup marker. Metadata is rechecked after acquiring the fence. Logical deletion proceeds without that fence. |

The new lock order was reviewed independently: upload source→document→version; deletion document→version; cleanup commits initial metadata updates before source→version and never requests document locks. No new lock-order cycle was identified in the bounded slice.

## Executed evidence

- Before fix: three cases fail on `077b8eb8`; [failure log](ingestion-final-gpt-evidence/regressions-red.log), [JUnit](ingestion-final-gpt-evidence/regressions-red.xml).
- After fix: those three cases pass; [log](ingestion-final-gpt-evidence/regressions-green.log), [JUnit](ingestion-final-gpt-evidence/regressions-green.xml).
- Full backend: **100 passed in97.11s**, exit0; [log](ingestion-final-gpt-evidence/full-backend.log), [JUnit](ingestion-final-gpt-evidence/full-backend.xml).
- Independent Spec follow-up: **25 document tests passed in21.62s**, exit0; [log](ingestion-final-gpt-evidence/independent-documents.log), [JUnit](ingestion-final-gpt-evidence/independent-documents.xml).
- Standards follow-up: no confirmed blocker in the repaired diff. The optional upload-parameter grouping smell remains nonblocking.
- Final exact-head hosted CI and merge SHA are recorded on [PR #20](https://github.com/Chookai/procurement-system/pull/20). Earlier passing heads are historical evidence, not a substitute for latest checks.

Tests used a uniquely named disposable PostgreSQL/pgvector container with temporary storage and a dedicated loopback port. They created/dropped only owned UUID schemas and injected fake Blob/embedding adapters. The application's stopped database services, existing volumes, secrets and original uncommitted checkout were untouched.

Commands (set DATABASE_URL to an explicitly owned test database):

```bash
uv sync --project backend --locked --python 3.12.3 --offline
uv run --project backend --locked python -m pytest backend/tests -q --junitxml=<output>
uv run --project backend --locked python -m pytest backend/tests/test_documents.py backend/tests/test_document_regressions.py backend/tests/test_document_lease_locks.py backend/tests/test_document_crash_recovery.py backend/tests/test_document_source_cleanup.py -q --junitxml=<output>
python3 tools/build-learnings.py
python3 tools/check-documentation.py
```

All final findings were reproduced before repair and independently verified afterward. No remaining blocking finding was identified. This does not establish production readiness, real-Azure behavior, full RAG quality, or fresh paid-provider/browser coverage. The previously reported API-equivalent cost comparison covers the earlier review turn and excludes this additional review, repair and merge turn.

Only the narrow implemented issue #18 is eligible for completion after merge; broader #12/#6 and the milestone remain open. The dirty main checkout remains preserved; merging the remote branch does not silently replace it.
