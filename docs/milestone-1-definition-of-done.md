# Milestone 1 definition of done

Status: approved by the user, 23 October 2026, including the primary HTTP API testing boundary and holdout evaluation protocol. This is an accepted completion contract, not a claim that the system is implemented. Candidate numeric quality thresholds still require development-baseline calibration before they are frozen. The end-of-phase user code inspection remains required.

## Outcome

One small fictional marine operations team completes a durable procurement journey using real backend authorization, document ingestion, retrieval and hosted model calls. The agent explains the purchase using current structured facts and cited evidence. Microsoft Foundry, external queue transport and Redis are not required for this phase.

## Completion gates

| Gate | Required observable behavior | Evidence |
|---|---|---|
| Reproducible local setup | Documented commands start the application, PostgreSQL/pgvector, Floci Blob adapter and ingestion runner. Versions are pinned and required SDK/provider capabilities have been checked. | Clean-start walkthrough, recorded versions and compatibility results. |
| Identity and authorization | Five seeded users authenticate using server-verified signed tokens. The backend checks effective permissions for browser and agent requests. A requester cannot approve their own request. Modified, expired or absent tokens cannot perform protected actions. No registration flow. | API-level positive and negative permission cases, including direct requests that bypass the UI. |
| Durable procurement | Aina submits a ten-unit PR at MYR 200 each; Ben approves; Chloe issues the MYR 2,000 PO; Dinesh accepts six; Eva captures and reviews a MYR 1,200 invoice. Four units remain outstanding. Records, version history and audit events survive application restart. | API journey and restart verification, plus a browser walkthrough. |
| Required exceptions | Return-for-change, PO reapproval/revision, partial goods receipt, damaged/rejected goods, one service-milestone acceptance case, multiple linked invoices and all three invoice review outcomes behave as specified. Repeated commands do not duplicate issued orders or accepted quantities. | Focused API scenarios and stored record/audit assertions. |
| Real evidence pipeline | Synthetic text-based PDFs, Markdown and plain-text sources can be uploaded, parsed, chunked, embedded and indexed. Source/version/passage references are preserved. Job retries are bounded and idempotent; replacement/deletion prevents stale evidence being used. Scanned-document OCR is deferred for this milestone. | Ingestion/retry/replacement/deletion cases against actual local storage and database. |
| Real RAG answer | The OpenRouter-backed Microsoft Agent Framework agent explains the four outstanding units using structured records and actual retrieved PO/receipt passages. Citations resolve to the right source version and passage. Unknown or inaccessible facts are not fabricated. Agent tools cannot approve, issue, accept, review or pay without the designated human action. | Recorded real-provider runs, answer/citation inspection and critical authorization/action checks. |
| Evaluation and operations | A local runner reports retrieval quality, factual/citation support, completeness, abstention, action/permission failures, latency and token/cost information where available. Every run records the corpus, dataset, model, prompt and retrieval configuration. Critical cases fail individually. Failures/retries have usable correlation IDs and no logged secrets. | Versioned machine-readable results, a short human-readable report and representative traces. |
| Usable workspace | The implemented UI supports the required workflow and source inspection in light and dark mode, including loading, empty, validation, denied-action and failure states. Login replaces the demo role switcher. | Browser smoke walkthrough in both themes and keyboard review of the main flow. |
| User code inspection | The user can inspect the implementation before milestone closure: module map, one API request through authorization/workflow/storage, document ingestion, retrieval/model execution, the evaluation runner and results, and known limitations. | Code walkthrough package and the user's review outcome. |

## Evaluation release protocol

- Turn the existing twelve seed scenarios into runnable corpus/snapshot fixtures. They are development and critical smoke cases, not a production benchmark.
- Add a separately reviewed holdout with at least twelve independent queries covering answerable questions, missing evidence, permissions, source freshness, numeric facts and malicious document instructions. Keep related document families and paraphrases on the same side of the development/holdout split.
- On tested critical cases, require zero unauthorized disclosure, unauthorized state changes, self-approval or prompt-injection-induced privileged actions. Require exact expected monetary/quantity facts and correct abstention for the designated negative cases.
- Measure Recall@5 and nDCG@5 on answerable, relevance-labelled cases. Report answer support, citation support and completeness separately; valid source IDs alone do not prove that claims are supported.
- Existing candidate quality targets are Recall@5 ≥ 0.90 and supported-citation precision ≥ 0.95. Calibrate using development data, agree the final thresholds, then freeze them before scoring the holdout. Record denominators and per-scenario results; do not tune on holdout failures and present the same set as untouched.
- Record p50/p95 latency and cost observations. Set any hard budgets from the selected model and development baseline before the final holdout run; no latency or cost value has been accepted yet.
- Deterministic CI can stub the external model endpoint, but real-RAG completion requires actual OpenRouter runs. Missing credentials, skipped hosted runs or mocked responses cannot produce a green milestone claim.

## Accepted testing boundary

Use the public FastAPI HTTP API as the main integration boundary for workflow, authorization, document/job behavior and agent requests. Run these tests against real local database/storage/worker dependencies. Stub only the paid external model boundary in deterministic tests; run provider contracts and held-out RAG evaluations separately against the selected real provider. Add a small number of browser journeys for UI wiring, forms, source previews and themes. Test externally observable behavior rather than private methods or exact generated prose.

There is no existing backend test suite to extend. The current prototype browser walkthrough is design evidence only. A future implementation must establish API integration fixtures and the evaluation runner.

## Explicit later work

Full production certification, real organizational identity, public registration, production network/secret configuration, backup/restore and load/recovery qualification belong to a later milestone. Also deferred: Foundry, RFQ/RFP/bidding, formal reconciliation, payments, scanned-document OCR, mandatory Redis and external queue transport. Exact provider/model versions remain configuration choices to validate, not fictional completed work.

The accepted architecture baseline can be implemented while compatibility work proceeds, but no milestone closes until the required local contracts, real-provider evaluations and user code inspection have evidence.
