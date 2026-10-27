# RAG evaluation contract

Status: initial plan and seed cases; no RAG pipeline or evaluation results exist yet.

The accepted runtime direction is Microsoft Agent Framework in Python, with OpenRouter as the first-milestone provider; Microsoft Foundry is deferred. Run the same cases against each exact provider/model configuration and store adapter/API mode, provider request IDs, fallback/routing metadata where available, and model parameters. Pin provider routing where supported for repeatable comparisons. Use a local executable evaluation runner with deterministic validators and a calibrated model judge where useful. Foundry evaluators are not a dependency for this phase; hosted scores do not replace tool-authorization or exact numeric checks. Add contract checks for streaming, tool calling, structured outputs, rate limits and timeouts before evaluating an adapter as production-ready.

## Evaluate separate layers

| Layer | Evidence and checks |
|---|---|
| Ingestion | Stable source/version/passage IDs, extraction accuracy for quantities and MYR amounts, page references, superseded/deleted source removal, idempotent reindexing |
| Retrieval | Recall@5 and nDCG@5 against labelled relevant passages; lexical baseline versus hybrid candidates; access and current-version filtering before context reaches the model |
| Answer | Correct facts, supported claims, valid citations, completeness, handling of conflicting/stale evidence, and abstention when evidence is absent |
| Agent | Correct read/draft tool selection, validated arguments, no unauthorized state changes, no self-approval, and rejection of instructions embedded in retrieved documents |
| Operations | Retrieval and end-to-end latency, token usage, estimated model cost, indexing lag, failures/retries, and correlation IDs |

Microsoft distinguishes retrieval-process evaluation from final-answer evaluation, including groundedness, relevance and completeness. Use those dimensions without treating a single LLM-judge score as sufficient: [Microsoft RAG evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators?view=foundry).

## Fixture and run contracts

The initial labelled cases are in [`evals/cases.jsonl`](../evals/cases.jsonl). Their source IDs are fixture contracts, not existing uploaded or indexed files. Create the synthetic source corpus and structured record snapshots from these contracts before measuring retrieval. Do not report absent-source or mocked responses as real RAG scores.

Each case records identity/role, query, applicable snapshot, relevant source IDs, expected facts, forbidden claims and tools, and whether abstention is required. Add passage-level relevance labels and graded relevance when the actual chunking scheme exists. Numeric facts such as outstanding quantity require exact deterministic checks against the structured snapshot; RAG prose cannot override those values.

Every real run must save dataset/corpus hashes, source versions, chunker/parser versions, embedding model/version, retrieval parameters, prompt version, generation and judge model/version, tool schema version, retrieved IDs/scores, full response/citations, tool calls/outcomes, and latency/token counts. Secrets and unauthorized source contents must not appear in logs. Human-adjudicate judge disagreements and critical failures.

Use development cases for prompt/retrieval tuning and a separately reviewed holdout for release decisions. Keep document families and paraphrases together when splitting to avoid leakage. Include English and Malay variants if both languages become supported. The small seed set is for designing the harness, not a statistically meaningful production benchmark.

## Proposed gates, pending baseline calibration

- Zero permission leaks, unauthorized state transitions, self-approvals, or prompt-injection-induced tool actions in the evaluated critical suite. These are observed results on tested cases, not a guarantee of universal safety.
- Exact expected monetary and quantity facts on deterministic workflow cases.
- Proposed retrieval Recall@5 of at least 0.90 on answerable labelled holdout cases; report results by scenario and access scope.
- Proposed supported-citation precision of at least 0.95, with groundedness and completeness also reported separately. Correct page/source existence alone does not establish claim support.
- Correct abstention on every seeded unanswerable/access-denied case; expand coverage before production.
- Track p50/p95 latency and per-answer cost first; set budgets after selecting a real model and measuring a baseline. No arbitrary performance promise is made now.

Use deterministic validators for permissions, tool calls, numeric facts, and source identities; use human-reviewed rubrics and optionally a calibrated model judge for semantic support and completeness. Fail critical cases individually even if aggregate quality is high.

## First executable milestone

Implement ingestion and a lexical retrieval baseline for one synthetic PO, one partial receipt, one invoice and one policy. Write a runner that loads the seed cases, invokes the real pipeline, captures the run contract, and exits nonzero for critical failures. Only then compare embedding/hybrid retrieval and generation. This plan does not claim that runner is implemented.
