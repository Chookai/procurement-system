# First durable procurement journey and evidence-backed agent

Status: ready-for-agent
Progress: In progress
Type: Specification

Approved by the user on 23 October 2026: milestone scope, completion gates, primary HTTP API testing boundary and holdout protocol. Published for implementation planning. Runtime/provider compatibility and final workspace layout remain tracked prerequisites for the affected work; this readiness label does not mark those checks complete.

## Problem Statement

The user wants to build and inspect a production-oriented RAG system and practice Azure architecture locally through a small, understandable procurement application. The current clickable design demonstrates workflows with in-memory records and simulated assistant responses, so it cannot yet demonstrate durable state, actual authorization, real document retrieval or measured model behavior.

## Solution

Implement a local, inspectable application for one fictional marine operations team. Users create and approve purchase requisitions, issue purchase orders, accept physical goods or service milestones, and review supplier invoices. An assistant answers procurement questions from authorized structured records and cited source evidence. A local evaluation runner makes retrieval, answer and action behavior measurable. End the phase with a code walkthrough and explicit limitations rather than a production-readiness claim.

## User Stories

1. As a learner, I want a reproducible local setup, so that I can inspect and change the complete application.
2. As a seeded user, I want to authenticate as my assigned identity, so that my actions use backend-verified permissions.
3. As a requester, I want to create a PR draft containing the business need, so that the approver can evaluate a concrete request.
4. As a requester, I want to record goods or services, quantities or milestones, MYR estimates, vessel/location and required date, so that procurement understands the need.
5. As a requester, I want to suggest a supplier without selecting the final supplier, so that procurement retains the buying decision.
6. As a requester, I want to edit and submit my draft, so that approval begins only when I am ready.
7. As an approver, I want to approve a submitted PR, so that procurement can prepare the PO.
8. As an approver, I want to return a request with a reason, so that the requester can correct it.
9. As a team member, I want self-approval prevented, so that a requester cannot authorize their own spending.
10. As a procurement buyer, I want to confirm supplier and price, so that the PO represents the intended purchase.
11. As a procurement buyer, I want to issue a PO from an approved request, so that a supplier order is explicit and traceable.
12. As a procurement buyer, I want proposed scope/value changes routed for reapproval, so that issued terms are not silently changed.
13. As a reviewer, I want previous PO versions preserved, so that I can understand which terms applied to each action.
14. As a receiver, I want to record multiple partial GRs, so that undelivered quantities remain visible.
15. As a receiver, I want accepted and damaged/rejected quantities distinguished, so that damaged goods do not count as fulfilment.
16. As a service acceptor, I want to accept completed milestones, so that services have evidence appropriate to work rather than physical delivery.
17. As an invoice reviewer, I want to capture and link supplier invoices before or after full receipt, so that documents can arrive in their actual order.
18. As an invoice reviewer, I want multiple invoices per PO, so that split billing is representable.
19. As an invoice reviewer, I want to record reviewed, needs clarification or rejected with a reason, so that the outcome is accountable.
20. As a team member, I want reviewed invoices to leave outstanding goods open, so that document review does not imply full delivery or payment.
21. As a team member, I want current state, linked documents, activity and the next PIC visible together, so that handoffs are understandable.
22. As a user, I want my records and audit events to survive restarts, so that a running browser is not the source of truth.
23. As a user, I want retries and conflicting updates handled consistently, so that I do not duplicate POs or receipts.
24. As an authorized user, I want to upload synthetic evidence, so that the agent can retrieve real indexed content.
25. As a user, I want ingestion status and failures visible, so that I can distinguish pending evidence from missing evidence.
26. As a user, I want replacement/deletion to remove stale searchable evidence, so that answers reflect valid source versions.
27. As a user, I want to ask why a purchase remains open, so that I understand the actual outstanding work.
28. As a user, I want numeric and workflow facts to come from structured records, so that generated text cannot change financial or fulfilment state.
29. As a user, I want citations that open the source version and passage, so that I can inspect support for an answer.
30. As a user, I want the assistant to say when evidence is absent or inaccessible, so that uncertainty is explicit.
31. As a team member, I want document instructions unable to grant authority, so that malicious source text cannot trigger privileged actions.
32. As a user, I want the assistant to prepare and explain while designated people authorize actions, so that accountability remains clear.
33. As a learner, I want retrieval quality measured separately from answer quality, so that I can diagnose the cause of failures.
34. As a learner, I want development and holdout queries separated, so that reported results are not tuning artifacts.
35. As a learner, I want critical permission and action failures to fail the run, so that aggregate quality cannot hide them.
36. As a learner, I want model/configuration versions, latency and usage recorded, so that I can compare runs fairly.
37. As a user, I want clear loading, validation, denied-action and failure states, so that the UI communicates what happened.
38. As a user, I want light and dark themes and basic keyboard navigation, so that the application remains usable across the explored visual modes.
39. As the project owner, I want a code walkthrough at phase completion, so that I understand the modules, request flow and evaluation results before accepting the milestone.

## Implementation Decisions

- Accepted baseline: React/TypeScript frontend, Python/FastAPI backend, one in-process Microsoft Agent Framework agent, PostgreSQL for workflow records and full-text/pgvector retrieval, Floci Blob-compatible document storage, durable database jobs and one ingestion runner. Foundry is deferred. Redis and an external queue are later scaling options.
- Accepted identity direction: five seeded identities for requester, approver, procurement buyer, receiver/service acceptor and invoice reviewer. Use server-verified signed tokens and backend permission checks; no registration in this phase. The implementation contract must specify login, expiry and role mapping. Client fields cannot establish identity or authority.
- Keep workflow/rules, identity, persistence, document ingestion, retrieval, model adaptation, evaluation and observability as explicit modules in one backend codebase. The agent module is not an independently deployed service.
- Persist purchase requisitions, approvals, issued PO revisions, goods receipts, service acceptances, supplier invoices/review outcomes, documents/source versions, audit events and ingestion jobs. Use exact MYR monetary representation, validated quantities, transactional updates, record versions and idempotent commands rather than floating-point totals or browser-owned state.
- Preserve independent PR, PO, fulfilment and invoice-review states. A UI summary status may prioritize an outstanding action, but it cannot replace those underlying facts. An issued PO remains a stable snapshot while a changed request is awaiting approval.
- Browser commands and agent tools enter the same authorization/workflow boundary. The agent may read authorized facts and prepare drafts. Approving spending, issuing POs, accepting goods/services and reviewing invoices require an authenticated designated person. Payment is outside scope.
- Initially route approvals to the designated approver for the small-team scenario. Do not invent or enforce a MYR amount threshold before the policy is confirmed. Hard budget enforcement is deferred.
- The durable sample orders ten pump seals at MYR 200 each, accepts six and reviews a MYR 1,200 invoice. The resulting outstanding quantity is four. Include a small service-milestone companion and the recorded workflow exceptions.
- Initial ingestion supports synthetic text-based PDFs, Markdown and plain text. Preserve document, version, source and passage identifiers plus access metadata. Extraction is real for supported types; scanned-document OCR is outside this milestone.
- Commit document metadata and ingestion jobs atomically, account for abandoned Blob uploads, use worker leases/bounded retries and idempotent version keys, and publish only complete index versions. Replaced/deleted sources cannot remain available as current evidence.
- Retrieval applies access and current-version filters before assembling model context. Evaluate a full-text baseline and a full-text/vector candidate. The selected embedding space is fixed per index version and shared by ingestion/query paths.
- OpenRouter is the real hosted-model route. Keep generation and embedding configuration separate. Select compatible models through a capability/baseline check; record streaming, structured output, tool and embedding support. All keys remain server-side. No unevaluated silent model fallback is part of this phase.
- Return answers with source-version/passage citations and factual record references. Missing evidence requires explicit uncertainty. Source text cannot override system rules, permission checks or tool policy.
- The main API contracts cover authentication, PR commands, PO issuance/revision, receipts/acceptances, invoices/review, document upload/status/source access and agent question/answer streaming. Commands validate identity, permissions, record state and version; failures produce actionable client responses and correlation IDs.
- Implement the selected workspace against those APIs. The first application slice uses the recommended register/detail layout as a delivery-team choice under the implementation authorization; ambient browser variant C was not treated as a user selection. Acceptance concerns behavior and accessibility. Preserve the accepted ADS light/dark foundation.
- Record traces and run metadata without keys or unauthorized content. The exact model packages, provider clients, Floci service operations and pgvector availability must be pinned/verified; the spec does not claim that compatibility work has already passed.
- The phase includes user inspection of implementation code and actual results before closure. The real PR/approval and PO issuance/revision/reapproval slices are implemented separately from the prototype; goods receipts/service acceptance are also implemented; invoice capture/review is also implemented; ingestion, agent tools/retrieval and real RAG evaluations remain pending.

## Testing Decisions

- Accepted main integration seam: the public FastAPI HTTP API, exercising identity, workflow, storage, ingestion jobs and agent requests through externally visible contracts. Prefer this high seam to mocking internal services or testing implementation-shaped methods.
- Use real local PostgreSQL, Blob adapter and worker fixtures for integration scenarios. Assert resulting records, supported state transitions, audit history, authorization failures and version behavior, rather than private call order or exact prose.
- Keep deterministic tests hermetic by stubbing the paid model endpoint only. Separately exercise the selected OpenRouter adapter and real hosted RAG. A skipped hosted run cannot count as real-RAG acceptance.
- Use a small browser smoke set for seeded-user login, the core handoffs, form errors, linked evidence and both color themes. The prototype's existing click-through notes are prior design evidence; there is no established backend integration suite yet.
- The evaluation runner uses the same agent/API boundary and versioned corpus fixtures. Convert the twelve seed cases to executable development/critical cases, then add at least twelve independently reviewed holdout queries across the required categories, without splitting related document families/paraphrases across tuning and holdout.
- Fail tested critical cases on any unauthorized disclosure/action, self-approval or malicious-document-induced privileged action. Verify exact workflow quantities/amounts and designated negative-case abstention deterministically.
- Report retrieval Recall@5/nDCG@5, answer support, citation support and completeness separately. Candidate targets are Recall@5 ≥ 0.90 and supported-citation precision ≥ 0.95, subject to development-baseline calibration and agreement before freezing the holdout protocol.
- Save source/dataset hashes, parser/chunker versions, models and parameters, provider/adapter mode, retrieval configuration, prompts, tool schemas, retrieved IDs/scores, answers/citations, tool results, latency and usage/cost data where available. Human-review semantic-judge disagreements and critical failures.
- Test retries, duplicate commands, conflicting edits, source replacement/deletion and worker retry exhaustion. Add operational latency/cost gates only after development measurement and before final holdout scoring.
- The user accepted the testing seam and milestone gates on 23 October 2026. Candidate numeric thresholds remain subject to development calibration; approval is not evidence that any implementation or evaluation has passed.

## Out of Scope

Microsoft Foundry, RFQ/RFP and bidding, formal reconciliation, payments, public registration, real ABL data/integrations, hard budget enforcement, assumed MYR approval thresholds, scanned-document OCR, mandatory Redis, external queue transport, microservices, distributed agent fleets and production certification. Real organizational identity, production Azure hardening, backup/restore and load/recovery qualification are later work.

## Further Notes

The business dataset is synthetic; the backend, authorization, ingestion, retrieval, hosted-model calls and evaluation evidence must be real for milestone completion. Exact provider/model capabilities remain to be checked. Lack of credentials or missing real-provider results must be reported as incomplete, not converted to simulated success. The user will inspect the code and results at the end of the phase.

This approved specification synthesizes the conversation and current project decisions. It does not authorize cloud provisioning or change the status of unverified compatibility work. The register/detail implementation choice and its validation are recorded in the first-slice walkthrough.

## Receiving while changes are reviewed

Accepted 26 October 2026 (ADR 0004): current issued PO fulfilment and pending PO change approval are independent workstreams. Dinesh receives against the active revision; pending terms grant no additional quantity. Preserve receipt revision/line references and revalidate replacements against accepted quantities at issuance, including receipts recorded after approval.
