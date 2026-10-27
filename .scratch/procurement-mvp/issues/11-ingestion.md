# PROC-011: Ingest versioned synthetic documents into a searchable corpus

Status: needs-triage
Progress: Not started
Type: RAG
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 04, 05

## Summary

Build the real upload, parsing, chunking and indexing path using synthetic procurement evidence.

## Proposed acceptance criteria

- [ ] Document/source/version/passage identifiers survive ingestion.
- [ ] Original documents are stored through the agreed Blob adapter.
- [ ] Durable jobs use leases, bounded retries and idempotent version keys.
- [ ] Readers see complete index versions; deletion and replacement remove stale evidence.
- [ ] Selected parser and embedding choices are recorded and reproducible.

## Open questions

- The exact retrieval backend and embedding model follow confirmed architecture/model choices.

## References

- docs/architecture-direction.md
- learnings/rag-evaluation-plan.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.
