# PROC-008: Issue purchase orders with revision and reapproval history

> Archived migration snapshot (27 October 2026). Track current work in [PROC-008 / GitHub #9](https://github.com/Chookai/procurement-system/issues/9).

Status: ready-for-agent
Progress: Done
Type: Feature
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 07

## Summary

Let the procurement buyer confirm supplier and commercial terms, issue a PO, and preserve revisions.

## Proposed acceptance criteria

- [x] Only the authorized buyer issues a PO from an approved PR.
- [x] Scope/value increases require reapproval.
- [x] The issued snapshot remains unchanged while a revision is proposed.
- [x] Duplicate command retries do not issue duplicate orders.

## Open questions

Initial issuance, revision proposals, reapproval and append-only issued history are implemented. Cross-module constraints for future receipts/invoices will be added with those modules; the overall milestone remains open.

## References

- docs/purchase-order-slice.md
- docs/po-revision-slice.md

- GLOSSARY.md
- docs/discovery.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: implemented buyer-only initial PO issuance, per-line approved price ceilings, immutable database snapshots, issued terms in the register, audit history and duplicate/conflict protection. Twenty-nine backend tests and browser/restart checks passed. Increases are blocked; revision proposals and the actual reapproval workflow remain unchecked, so this broader ticket stays In progress.

24 October 2026: completed frozen PO proposals, Ben approval/return, Chloe issuance of exact approved terms, first issuance after reapproval, append-only issued revisions and browser history. Thirty-nine backend tests passed, including real PostgreSQL rollback/concurrency/authorization checks; browser review/return/issuance, themes/mobile and actual API process restart passed. See runtime-results/po-revisions-browser.json and po-revisions-restart.json. Updated code walkthrough and lesson 0004. Full milestone and user code inspection remain pending.
