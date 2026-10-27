# Mission: Evaluate a procurement RAG system

## Why
Build and inspect a production-oriented RAG agent for the mocked procurement project, while improving architecture design skills. Understand each evaluation decision generally and then translate it to Azure without adding infrastructure before it is needed.

## Success looks like
- Diagnose whether a failed answer came from ingestion, retrieval, generation, or agent authorization.
- Design labelled cases, reproducible runs, and release gates that expose incorrect quantities, weak citations, and unauthorized actions.
- Explain how the same evaluation contract fits the local baseline and a future Azure deployment.
- Inspect the implementation and explain what its evidence proves and what remains untested.

## Constraints
- Start small: one team, five seeded PICs, synthetic documents, MYR.
- First milestone: local runner, PostgreSQL retrieval, Floci Blob, OpenRouter; Microsoft Agent Framework direction accepted, compatibility still to validate.
- Microsoft Foundry is deferred. Azure mappings are teaching proposals, not deployed infrastructure.
- Teach in two lenses: general concepts first, then Azure specifics. Use short practical exercises from this project.

## Out of scope
- RFQ/RFP/bidding, reconciliation and payments in this milestone.
- Claiming production readiness from a small seed dataset or claiming learning from reading alone.
