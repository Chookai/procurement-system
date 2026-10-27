# PROC-012: Answer procurement questions with current state and cited evidence

Status: needs-info
Progress: Not started
Type: RAG
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 05, 06, 08, 09, 10, 11

## Summary

Use Microsoft Agent Framework with the configured hosted-model adapter to answer questions from authorized records and source passages.

## Proposed acceptance criteria

- [ ] The agent explains why a ten-unit PO with six accepted units remains open.
- [ ] Numeric facts and workflow status come from authorized structured records.
- [ ] Citations identify actual indexed source versions and passages.
- [ ] The answer distinguishes missing evidence from known facts.
- [ ] Generation and embedding providers are configured separately and model changes are evaluated.
- [ ] Agent actions cannot bypass designated human authorization.

## Open questions

- Initial routes and credentials are verified for integration; release model identity and quality still need actual RAG evaluation. Foundry remains excluded.

## References

- docs/runtime-compatibility.md

- docs/architecture-direction.md
- learnings/rag-evaluation-plan.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: verified initial OpenRouter generation and embedding routes with real calls. Server-side credentials are configured. The five passing provider probes do not implement retrieval, authorization or citations; this ticket remains Not started.
