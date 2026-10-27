# PROC-009: Record partial goods receipts and service acceptance

> Archived migration snapshot (27 October 2026). Track current work in [PROC-009 / GitHub #10](https://github.com/Chookai/procurement-system/issues/10).

Status: ready-for-agent
Progress: Done
Type: Feature
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 08

## Summary

Record accepted delivery quantities or service milestones while keeping outstanding fulfilment visible.

## Proposed acceptance criteria

- [x] Multiple goods receipts or service acceptances can reference one PO.
- [x] Accepted and damaged/rejected quantities are distinct.
- [x] Only accepted quantities count toward fulfilment.
- [x] The API validates limits and preserves audit history under retries.

## Open questions

Receiving against issued revisions follows ADR 0004. Invoice-aware amendment rules and audited receipt correction remain future scope.

## References

- GLOSSARY.md
- docs/discovery.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

26 October 2026: user authorized the next slice after accepting ADR 0004. Record partial goods receipts and service milestone acceptance as Dinesh, preserve revision/line references, expose fulfilment alongside PO change status, and revalidate revisions at issuance against intervening receipts.

26 October 2026: implemented receiver-only goods receipts and service acceptances, immutable revision-linked history, accepted/damaged/rejected/outstanding figures, separate fulfilment and PO-change visibility, and receipt-aware revision constraints with revalidation at issuance. All 54 backend tests, receiving browser checks and actual API restart passed. Walkthrough: docs/receiving-slice.md; lesson: learnings/lessons/0005-receipts-and-revisions.html. Full milestone and user code inspection remain open.
