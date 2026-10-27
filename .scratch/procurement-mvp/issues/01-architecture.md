# PROC-001: Confirm the first milestone architecture

Status: ready-for-agent
Progress: Done
Type: Decision
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: None

## Summary

Confirm a small implementation architecture for one durable procurement journey and a real RAG answer.

## Proposed acceptance criteria

- [x] Record accepted choices separately from optional future services.
- [x] Confirm PostgreSQL/full-text/pgvector, Blob storage and a single ingestion runner.
- [x] Decide the initial identity approach: five seeded users, server-verified signed tokens and backend role checks; no registration.
- [x] Verify required Floci service operations and compatible runtime versions.
- [x] Keep Redis and external queue transport optional until measured need.

## Open questions

None for this compatibility decision. Application implementation and quality evaluation remain separate tickets.

## References

- docs/runtime-compatibility.md

- docs/architecture-direction.md
- docs/adr/0001-human-authorization.md
- docs/adr/0002-small-openrouter-first-baseline.md
- docs/adr/0003-seeded-local-identity.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

22 October 2026: user accepted the baseline with Foundry excluded from phase one. Microsoft Agent Framework stays; OpenRouter supplies model access. Code inspection is required at phase completion. Ticket remains needs-info / In progress because identity and compatibility verification are unresolved.

23 October 2026: initial local identity is accepted. Only compatibility and local-service verification remain open on this architecture ticket; the earlier identity question is resolved. This does not mean authentication has been implemented.

23 October 2026: completed compatibility verification with digest-pinned Floci AZ 0.15.0 and PostgreSQL 17.11/pgvector 0.8.7, locked Python dependencies, real Blob/database/restart checks, five live OpenRouter contracts and four simulated error cases. Architecture decision work is Done; no procurement backend or RAG quality result is claimed. See the compatibility report and runtime-results artifacts.
