# Text policy ingestion review and Kilo comparison

1 November 2026. Issue #18, part of #12. PR: https://github.com/Chookai/procurement-system/pull/20

Base: `7c9f4bff0290db87a52cf5cad1d4f38db7b70057`.
Initial frozen review: `3be28d714211c33303f0feaed5b7ce7aa7fceb07`.
First repair: `ca50fe05361de6c1eac65c5d7d1e31e8cfd0524d`.
Final code candidate: `53648aff9a914b8df6f1ec4191d830ebb00c3abe`.
Later commits publish review evidence; they do not change application behavior.

## Result and protected boundaries

Three actionable defects were repaired: lease expiry across database lock waits, valid-source passage limits, and replacement upload retry identity. Independent review ran separately from implementation; follow-up review required a second lease repair. Shared-policy authorization, fixed embedding route, issued-PO rules and invoice/payment boundaries remain as specified. No merge, deployment, issue closure or agent-answer feature was performed. All original uncommitted work remains in the Linux checkout; the PR was prepared in an isolated clone.

## Standards

Independent reviewer: zero confirmed documented-standard violations; one optional Data Clumps heuristic around the upload command parameters, left unchanged. The reviewer also independently reproduced the source-size defect and noted the UI retry concern before execution. Heuristics are not acceptance blockers.

## Spec and repairs

| Finding | Evidence before | Final behavior / ownership |
| --- | --- | --- |
| P1: publication checks transaction-start time after waiting for a document lock | Lease already expired but original candidate publishes; `lease-wait-before.json` | Acquire document then job lock, check database wall clock afterward, and guard completion after inserts. Codex executed the defect; Kilo supplied useful real-clock repair logic, adapted by the orchestrator. |
| P2: accepted UTF-8 policy exceeds hard 80-passage limit | Valid 65,509-byte and 65,536-byte sources fail chunking; `regressions-before.log` | Derive ceiling from shared 64 KiB source limit and minimum 451-character advance; preserve 1,200-character chunks, 150-character overlap and line citations. Codex reproduced; reasoning-enabled Kilo patch had the correct bound in substance. |
| P2: replacement retry loses original key and expected generation after refresh | Chromium mock records generation 1/key A then generation 2/key B after 503; `replacement-retry-before.json` | Preserve the original command key and generation across transient failure; clear an ended attempt on conflict. Kilo raised the concern; orchestrator independently reproduced and repaired it. Codex Standards also noted it as an unverified suspicion. |
| Lease repair follow-up: renewal can revive an expired job after a row-lock wait | First repair passes 20 tests, but a new independent test fails; `renewal-before.log` | Explicitly acquire job lock before guarded renewal/update. Keep the final publication guard. Codex follow-up reproduced this before acceptance. |

The last row is another location of the lease-contract defect, not an additional independent product issue. The first repaired candidate is superseded.

## Kilo / DeepSeek comparison

Kilo CLI 7.8.18 used the exact `kilo/deepseek/deepseek-v4.1-flash` route. Both reviewers evaluated the initial frozen code. Codex used two independent reviewer contexts with repository/test access. Kilo received a 73,945-character source/spec bundle with all tools denied. This controls the snapshot, but not reviewer access or effort; it is one case, not a model benchmark.

| Task | Outcome | Reported USD | Kilo-reported elapsed |
| --- | --- | ---: | ---: |
| Default reasoning review | Length limit; 32,000 reasoning tokens, no answer. CLI exit 0 was not treated as review success. | 0.028570 | 244.687s |
| Non-thinking review retry | Returned 19 labelled sections, most self-dismissed. UI retry concern confirmed; lease-renewal recommendation rejected. | 0.006610 | 34.676s |
| Default reasoning repair | Useful clock/bound logic; patch hunks did not apply directly. Adapted and strengthened, then regression tested. | 0.021341 | 158.164s |
| Non-thinking repair | Rejected: contradictory patches and a 110-passage cap that does not cover the minimum advance. | 0.002813 | 13.804s |

Review inference total: **USD 0.0351797394**. Repair proposals: **USD 0.0241536594**. Total Kilo-reported inference: **USD 0.0593333988**. These are CLI usage events, not reconciled billing. Codex API-equivalent estimates are now calculated from the local usage records below. Actual Codex subscription charges remain unknown; different work scopes prevent an equal-work dollar-saving claim. Kilo totals exclude test, CI and orchestration work; the separate Codex complete-task estimate includes recorded inference for that work. Some calls ran concurrently. Two initial CLI setup/attachment failures occurred before model invocation.

Kilo's F5/F16 recommendation to renew/publish an expired lease conflicts with the approved fencing requirement and was rejected. Its long-batch example also assumed 16 sequential 20-second requests, while the adapter sends one bounded batch request. F2 relies on manual database mutation; F14 describes harmless duplicate idempotent cleanup. Other sections mostly state accepted scope or self-dismiss concerns; they are not counted as confirmed defects. Full raw final answer and both repair proposals are preserved beside `comparison.json`.

Practical result for this case: Kilo provided a useful UI lead and repair material for about six cents, but execution and independent follow-up caught defects or unsafe advice that static model output alone did not resolve.

## Codex versus Kilo: findings, resolution and cost

The initial review snapshot was `3be28d71` for both systems. Codex used two GPT-6.1 Sol reviewer contexts with repository and execution access. Kilo used DeepSeek V4.1 Flash with a static 73,945-character bundle and tools denied. Do not equate narrative finding counts with confirmed defects.

| Dimension | Codex review and orchestration | Kilo / DeepSeek V4.1 Flash |
| --- | --- | --- |
| Lease expiry and fencing | Reproduced expiry during document-lock wait; later caught renewal after a job-lock wait; verified rollback and repair. | Did not identify the actual transaction-clock/lock-wait defect in the initial review. F5/F16 instead recommended allowing expired leases; rejected. Its later prompted reasoning repair supplied useful real-clock logic but needed adaptation and follow-up. |
| Valid source chunk limit | Independently reproduced valid 65,509-byte and 65,536-byte failures; verified complete reconstruction and citations after repair. | Did not identify the hard-cap defect in the initial review. After being supplied the defect, reasoning repair derived a useful bound; non-thinking repair's 110-passage bound was insufficient and rejected. |
| Replacement retry identity | Standards reviewer initially suspected it; orchestrator then reproduced it in isolated Chromium and implemented/verified the repair. | F19 independently flagged the same UI risk. This was the useful review lead confirmed by execution; it is shared discovery, not a unique Kilo find. |
| Finding quality | Two executed defect families in initial review, one optional standards smell; later verified the UI defect and renewal variant. | Nineteen labelled sections, mostly self-dismissed or accepted design choices. One confirmed UI concern; unsafe lease advice and unsupported concerns were excluded from confirmed counts. |
| CI resolution | Ran/checks and inspected hosted CI; added six backend regressions. Diagnosed local 401s with an independent clock probe without relaxing authorization. | No hosted CI job was delegated to Kilo, and it did not execute tests or diagnose CI. Its CI-resolution ability is unmeasured in this case. |
| Repair resolution | Orchestrator integrated/repaired changes, ran regressions and obtained independent follow-up before acceptance. | Repair proposals were reviewed, not applied blindly. Default patch hunks failed application; non-thinking output was contradictory and used an inadequate bound. |
| Timing | Comparable isolated reviewer latency was not recorded. End-to-end work includes tests, CI waits and reporting. | Default review 244.687s with no answer; non-thinking retry 34.676s. Prompted repairs 158.164s and 13.804s. These are Kilo-reported elapsed values, not equal-work end-to-end timings. |

There were no hosted CI failures requiring repair in this experiment. Earlier green CI still missed the edge cases; the new regression cases make them executable acceptance evidence. Do not credit either model with resolving a nonexistent hosted failure.

### API-equivalent Codex cost

Using [published GPT-6.1 Sol pricing](https://developers.openai.com/api/docs/models/gpt-6.1-sol), Standard rates per million tokens are USD 2.00 uncached input, 0.10 cached input and 10.00 output. Fast is twice Standard. The recorded cache-write count is zero; every request is below the 272K long-context threshold. Regional surcharges are not assumed. [Reasoning tokens](https://developers.openai.com/api/docs/guides/reasoning) are already part of output and are counted once.

| Scope | Codex Standard API equivalent | Codex Fast sensitivity | Kilo-reported inference |
| --- | ---: | ---: | ---: |
| Initial independent reviews only | $0.405076 | $0.810152 | $0.0351797394, including unsuccessful reasoning attempt |
| All reviewer work, including regressions, clock diagnosis and repair verification | $1.2272528 | $2.4545056 | No matching execution scope |
| Main Codex agent: coordination, integration/repairs, CI inspection and reports | $2.4885896 | $4.9771792 | No matching orchestration scope |
| Complete previous Codex task / all Kilo review and repair calls | $3.7158424 | $7.4316848 | $0.0593333988, static model calls only |

The initial-review row is included in all-reviewer work; do not add it again. Likewise, the complete-task row already includes reviewers plus the main agent. These are estimated API equivalents, not Codex subscription charges. The service tier is not recorded, so Standard and Fast are shown as scenarios.

| Whole-task token category | Recorded tokens | Standard rate / 1M | Estimated USD |
| --- | ---: | ---: | ---: |
| Uncached input | 181,756 | $2.00 | $0.363512 |
| Cached input | 27,288,704 | $0.10 | $2.7288704 |
| Output, including 19,883 reasoning tokens | 62,346 | $10.00 | $0.623460 |
| Total | 27,532,806 | — | $3.7158424 |

Method: sum each request's `last_token_usage`, not repeated cumulative totals. The 27,470,460 total input tokens include cached input; cached tokens are subtracted before uncached pricing. The scope begins with the user's “yes proceed” review authorization and ends before the later cost-calculation request. Earlier project work, this calculation/report update, unrecorded platform work and internal permission-review guardians without public model rates are excluded. The repeated large conversation context is reflected in the usage, so token totals are not unique source-text size.

[Full usage calculation](ingestion-review-evidence/codex-api-equivalent.json) · [Combined machine-readable comparison](ingestion-review-evidence/comparison.json).

### Assessment for this case

Codex supplied deeper executable failure analysis and validated the repaired system. Kilo supplied an inexpensive corroborating UI lead and some useful prompted repair material, with unsafe or incomplete output caught by the verification loop. A sensible next experiment would give both reviewers the same tool access, task boundaries and required tests. This single unequal-work run does not establish a general quality ranking, CI-resolution winner or interchangeable cost saving.

## Executed verification and limits

- Initial frozen candidate: fresh locked Linux installs; frontend types/build, prototype build, learning generation/links and tracked-file hygiene passed. Hosted run [41275792069](https://github.com/Chookai/procurement-system/actions/runs/41275792069) passed both jobs, including 91 backend tests.
- First repair: 18 targeted cases passed before coverage expanded; four new regression cases then passed. Isolated Chromium replacement retry went from exit 1 to exit 0; frontend types/build passed. Independent first-repair run passed all 20 document cases. Hosted run [41276503790](https://github.com/Chookai/procurement-system/actions/runs/41276503790) passed both jobs, including 95 backend tests. This candidate is superseded by the job-lock fix.
- Final code: orchestrator ran all 22 document/lease/regression cases: 22 passed in 20.61s. Independent final run: 21 passed/1 transient authentication failure in 18.75s; that case alone passed, then the unchanged full rerun passed all 22 in 18.77s. Results are preserved in `independent-final-documents.xml` and the accompanying log; failed attempts remain beside them. The six new regression cases are credential-free and are automatically discovered by existing backend CI.
- Local full-suite failures are recorded, not relabelled as passes: initial 89 passed/2 failed; repeat 90 passed/1 failed. Failures were transient authentication errors in unchanged procurement tests. An independent pure JWT probe recorded six immature-token errors across 680,963 roundtrips, coincident with backward wall-clock steps around 0.85s. Identity, configuration and locks are unchanged from base. No authentication relaxation or host-clock changes were made.
- The exact final hosted SHA and result are recorded in [PR checks](https://github.com/Chookai/procurement-system/pull/20/checks) and the PR description after the final evidence commit. Follow the latest head, not the earlier passing runs.
- No fresh full upload/search/replacement/delete browser journey with real embeddings, paid live ingestion probe, frozen retrieval holdout, answer evaluator or hosted failing-artifact test was run in this review. Historical implementation probes remain explicitly historical. The new browser retry test intercepts every API call and uses synthetic responses; it does not prove real provider availability.

## Reproduce

From the candidate checkout with locked Python and existing disposable/isolated-schema-compatible PostgreSQL:

```bash
uv sync --project backend --locked --python 3.12.3
uv run --project backend --locked python -m pytest backend/tests -q
uv run --project backend --locked python -m pytest backend/tests/test_documents.py backend/tests/test_document_regressions.py backend/tests/test_document_lease_locks.py -q
npm ci --prefix frontend
npm run app:check
npm run app:build
python3 tools/build-ticket-register.py
python3 tools/build-learnings.py
python3 tools/check-documentation.py
```

Browser retry harness: start candidate Vite on unused port 5186; run `node docs/verification/ingestion-review-evidence/replacement-retry.cjs /absolute/path/to/playwright`. Set `RETRY_BASE_URL`, `PLAYWRIGHT_CHROMIUM_EXECUTABLE` and `RETRY_EVIDENCE` as needed. All API requests are intercepted. This is a supplemental local regression, not the separate portable browser CI project.

Inspect before merging: buyer-only writes and read-only roles, immutable source versions, replacement/deletion publication semantics, migration 006 and lease fencing. Issues #18/#12/#6 stay open; agent tools, generated answers, confidential evidence, PDF and Azure deployment remain later work.
