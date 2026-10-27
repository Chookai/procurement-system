# Application architecture and RAG resources

Reviewed 23 October 2026. These sources ground the lessons; procurement examples and proposed deployment choices are project-specific applications.

## Knowledge

- [William Y. Arms, Digital Libraries: Information Retrieval, Evaluation](https://www.cs.cornell.edu/wya/DigLib/text/Chapter10.html#)
  University-hosted foundational text. Use the Evaluation section for precision and recall and the need for relevance labels.
- [Microsoft: RAG LLM evaluation phase](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-llm-evaluation-phase)
  Use for separating correctness, grounding and completeness when evaluating generated answers.
- [Microsoft: RAG evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators)
  Use for process versus system evaluation and Foundry terminology. Its LLM-judged Retrieval score is not labelled Recall@k. Foundry is optional future tooling here.
- [Microsoft: RAG information retrieval](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-information-retrieval)
  Use when comparing retrieval configurations. Azure AI Search-specific settings must not be copied into our PostgreSQL configuration.
- [Microsoft: pgvector on Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgvector)
  Use for the future managed PostgreSQL mapping; Azure requires allowlisting and enabling the `vector` extension. This does not verify our local runtime.
- [Microsoft: Application Insights and OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
  Use for Azure runtime observability. Telemetry complements our quality evaluation; a successful trace is not a correctness score.

## Application components: primary reading

- [React: Your First Component](https://react.dev/learn/your-first-component)
  Use to explain UI components and composition. Current docs use a newer React release; our lesson uses concepts supported by the installed React 18 app.
- [React: State, a Component’s Memory](https://react.dev/learn/state-a-components-memory)
  Use to distinguish selected-row UI memory from database persistence.
- [React: Passing Props](https://react.dev/learn/passing-props-to-a-component)
  Use for the actual App → RequisitionForm values and callback boundary.
- [FastAPI: First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/)
  Use for HTTP path/method handlers; file naming is a project convention.
- [FastAPI: Request Body](https://fastapi.tiangolo.com/tutorial/body/)
  Use for Pydantic body parsing/validation, distinct from business permission checks and SQL tables.
- [TypeScript: The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)
  Use for erased types and why frontend type annotations are not network-data validators.

- [PostgreSQL: Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
  Use for grouping PO, PR version, audit and retry writes atomically. Current docs describe PostgreSQL 18; our verified runtime is PostgreSQL 17.

## Wisdom (Communities)

- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/)
  Optional venue for Azure practitioner questions. Bring a minimal reproduction and sanitized run evidence; verify answers against documentation and measurements. No community participation is required or initiated.

## Gaps

- Initial generation/embedding routes and compatible package versions were live-tested; release-quality model selection and judge calibration remain open. See `../docs/runtime-compatibility.md`.
- Floci Blob operations, PostgreSQL/pgvector and graceful restart passed executable checks. The first PR API/UI slice is verified; the ingestion/retrieval/application path for real RAG still needs end-to-end validation.
- The synthetic corpus, passage labels, independent holdout and calibrated judge do not exist yet.
- No latency/cost baseline or production benchmark exists. Candidate gates are proposals, not measured results.

## PO reapproval lesson (24 October 2026)

- [PostgreSQL 17: Transactions](https://www.postgresql.org/docs/17/tutorial-transactions.html) — version-matched primary explanation of atomic commits and rollback; applied to issuance plus audit.
- [Azure Database for PostgreSQL overview](https://learn.microsoft.com/en-us/azure/postgresql/overview) — verified managed database mapping; our procurement authorization remains application logic. Azure deployment is still proposed.

## Receiving lesson (26 October 2026)

- ADR 0004 and docs/receiving-slice.md ground the project-specific receiving rules and conservative revision constraints.
- PostgreSQL 17 Transactions and the Microsoft managed PostgreSQL overview above ground the transaction and future Azure mapping in lesson 0005.
- [Oracle Change Orders](https://docs.oracle.com/en/cloud/saas/procurement/26b/oaprc/change-orders.html) preserves current issued terms during change processing; [SAP ByDesign receiving restriction](https://userapps.support.sap.com/sap/support/knowledge/en/1886136) illustrates that another system may block receiving during reapproval. These sources informed the explicit local policy; they do not establish a universal industry rule.

## Invoice lesson (26 October 2026)

- [PostgreSQL 17: Unique constraints](https://www.postgresql.org/docs/17/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS) — verified primary source for uniqueness across a column combination; applied to normalized supplier + invoice number.
- docs/invoice-slice.md and existing project scope define the review/payment and quantity boundaries. These are project rules, not a universal accounting policy.
