# PROC-006: Persist purchase requisitions and their activity history

Status: ready-for-agent
Progress: Done
Type: Feature
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 04, 05

## Summary

Let a requester save and submit a durable purchase requisition for a business need.

## Proposed acceptance criteria

- [x] Drafts capture goods/service type, quantity or milestones, MYR estimate, purpose, vessel/location, supplier suggestion and required date.
- [x] An authorized requester can edit a draft and submit it.
- [x] Records and audit history survive restart.
- [x] Validation and concurrent-edit behavior are defined at the API boundary.

## Open questions

None recorded beyond prerequisite decisions.

## References

- docs/first-application-slice.md

- GLOSSARY.md
- docs/discovery.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: Implemented durable validated goods/service PR drafts, edits, submission, exact MYR estimates, optimistic versions, idempotent commands and activity history. HTTP integration tests and actual API process restart verification passed. This does not close the overall milestone or implement PO, fulfilment, invoices or RAG.
