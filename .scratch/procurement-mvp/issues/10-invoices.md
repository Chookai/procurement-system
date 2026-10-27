# PROC-010: Capture and review supplier invoices without authorizing payment

> Archived migration snapshot (27 October 2026). Track current work in [PROC-010 / GitHub #11](https://github.com/Chookai/procurement-system/issues/11).

Status: ready-for-agent
Progress: Done
Type: Feature
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 08, 09

## Summary

Capture multiple supplier invoices, link evidence and record a human review outcome.

## Proposed acceptance criteria

- [x] Invoice capture can happen before full receipt.
- [x] The reviewer chooses reviewed, needs clarification or rejected with a reason.
- [x] Invoice review leaves outstanding delivery quantities open.
- [x] Review never marks payment completed or formal reconciliation performed.

## Open questions

Commercial corrections/resubmission, reopening final reviews, tax/freight/credit notes, document binary ingestion, formal reconciliation and payment remain outside this slice.

## References

- GLOSSARY.md
- docs/discovery.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

26 October 2026: user authorized invoice capture/review after receiving. Implement Eva-only capture/review, issued PO revision and optional receipt links, immutable captured values and append-only reasoned review outcomes, duplicate supplier invoice protection, independent invoice/fulfilment visibility, and advisory discrepancy checks. No payment or formal reconciliation.

26 October 2026: completed Eva-only invoice capture/review, multiple invoices per PO, reasoned reviewed/needs-clarification/rejected outcomes, captured PO and receipt evidence, advisory discrepancy checks with frozen review snapshots, duplicate supplier invoice protection and independent invoice/fulfilment UI. All 75 backend tests, actual browser journey and API restart passed. See docs/invoice-slice.md, runtime-results/invoices-browser.json and invoices-restart.json. Lesson 0006 added. Ingestion, agent/RAG/evaluations and user code inspection remain open for the overall milestone.

27 October 2026: fixed cross-selection invoice display reported in browser comments. Duplicate sibling React keys left PR-0014 invoice nodes on PR-0013. Namespaced invoice/PO review keys, cleared old notices on selection, and added the read-only repeated-switch regression in tools/check-selected-pr.cjs. It passed across four PIC roles, matching invoice/PO/receipt/activity data, resetting unsaved review state and reporting no duplicate-key warnings. Business data unchanged.
