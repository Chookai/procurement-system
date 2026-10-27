# PROC-004: Establish the React and FastAPI application boundary

Status: ready-for-agent
Progress: Done
Type: Infrastructure
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 01, 02, 03

## Summary

Create the real application foundation with clear workflow, agent, ingestion and evaluation modules.

## Proposed acceptance criteria

- [x] React/TypeScript uses a versioned FastAPI contract.
- [x] A reproducible local command starts the supported dependencies.
- [x] Secrets remain on the server and the UI handles API failures.
- [x] Prototype code is treated as a design reference, not promoted wholesale.

## Open questions

None recorded beyond prerequisite decisions.

## References

- docs/first-application-slice.md

- docs/architecture-direction.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: Implemented a separate React/FastAPI application boundary, versioned HTTP contract, dependency startup commands and server-side credentials. The prototype remains separate; document, agent and evaluation modules will be added in subsequent slices. This does not close the overall milestone or implement PO, fulfilment, invoices or RAG.
