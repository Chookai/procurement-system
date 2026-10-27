# PROC-007: Implement human approval and return for changes

> Archived migration snapshot (27 October 2026). Track current work in [PROC-007 / GitHub #8](https://github.com/Chookai/procurement-system/issues/8).

Status: ready-for-agent
Progress: Done
Type: Feature
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 06

## Summary

Let the designated approver approve a submitted PR or return it for correction.

## Proposed acceptance criteria

- [x] Only a submitted PR can be approved by an authorized person.
- [x] Return-for-change captures a reason and gives ownership back to the requester.
- [x] Approval and resubmission are auditable.
- [x] No MYR threshold is invented; initial routing follows the confirmed policy.

## Open questions

None for the first-team approval route: Ben handles submitted PRs without a spending threshold or automatic approval.

## References

- docs/first-application-slice.md

- docs/discovery.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: Implemented Ben approval and reasoned return-for-change, including edit/resubmission and auditable versions. Self-approval, invalid transitions, stale versions and competing approvals are covered by real-database HTTP tests. This does not close the overall milestone or implement PO, fulfilment, invoices or RAG.
