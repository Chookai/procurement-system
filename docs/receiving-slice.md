# Goods receipt and service acceptance

Implemented 26 October 2026 for the local synthetic procurement application. Decision: [ADR 0004](adr/0004-receive-against-issued-po-revisions.md). Invoices are now implemented in the [invoice slice](invoice-slice.md); ingestion and the production-oriented RAG/evaluation journey remain pending.

## Try the flow

1. Sign in as `dinesh` (local demo password `harbor-demo`). Select an issued PO. Its fulfilment panel sits near the top, below the PO change action panel.
2. Choose **Record goods receipt** or **Record service acceptance**. Enter the delivery/work reference, inspection date and quantities. Notes are required for any damaged or rejected quantity. Service milestones must be whole numbers; damaged goods are not a service outcome.
3. Confirm. The panel updates accepted, damaged, rejected and outstanding figures for each issued line. Expand **Receipt and acceptance history** for the actor/time, evidence reference, original revision and quantities.
4. Use **Filter by fulfilment** to find awaiting, partial or complete orders independently of the PO change status filter.

Only Dinesh’s receiver role may confirm receipts/acceptances. Other authorized readers can inspect the figures and history. A completed order has no receiving action; a later issued increase can make it outstanding again. Receipt completion is neither invoice review nor payment.

Example: revision 1 orders 10 seals. Dinesh records 6 accepted, 2 damaged, 1 rejected. Outstanding is `10 - 6 = 4`, not 1. These damaged/rejected outcomes await replacement or another resolution; they do not become accepted inventory through this record. Multiple receipt attempts can accumulate damaged/rejected counts, so those historical counts are not subtracted from ordered quantity.

## Two concurrent workstreams

| Current issued PO | Change proposal | What Dinesh may do |
|---|---|---|
| Revision 1: 10 ordered, 6 accepted, 4 outstanding | Increase to 12 awaits Ben | Receive up to the 4 outstanding, not the proposed 6 |
| Same issued revision | Ben approved; Chloe has not issued | Still receive against revision 1 |
| Revision 2 issued: 12 ordered, same 6 accepted | Proposal issued | Receive the remaining 6 against revision 2 |

Each receipt stores its issued revision and line positions plus the original commercial snapshot. A new revision does not relabel or reprice historical receipts. The register shows fulfilment separately from change approval; Dinesh remains able to act while Ben reviews a change.

If Dinesh accepts 9 after Ben approves a proposed decrease to 8, Chloe’s issuance fails. Ben can return the approved proposal with a reason, and Chloe submits corrected terms for fresh review. Approval and issuance both validate against receipts, and issuance validates again because receiving can happen between them.

## Code and public contract

```text
React: Receiving.tsx
  ReceivingPanel → Record goods receipt / service acceptance
  ReceiptForm → main.tsx receive() → api()
FastAPI: app.py
  POST /api/v1/requisitions/{id}/receipts
  contracts.py RecordReceipt validates fields and nonzero unique lines
workflow.command("receive")
  signed receiver role + CSRF + retry key
  lock PR; validate expected PR version
receiving.record_receipt()
  require current issued PO revision
  check accepted + damaged + rejected <= outstanding per line
  enforce whole service milestones; no service damaged quantities
  INSERT immutable receipt with issued snapshot
workflow.command()
  increment PR version + append audit + save retry response
  commit together
```

Request fields: `expected_version`, `po_revision`, `received_on` (date), `reference` (2–150 characters), optional `notes` (up to 2,000), and `lines` (1–20 entries containing `line_index`, `accepted`, `damaged`, `rejected`). Quantity strings are exact decimals with at most two fractional digits. Missing outcome quantities default to zero; duplicate line indices, zero-only lines, negative/over-precision quantities and unknown issued lines fail validation. All PR mutations require `Idempotency-Key`, the session cookie and `X-CSRF-Token`.

The returned PR includes `receipts` and `fulfilment`. `fulfilment.lines` contains per-line `ordered`, `accepted`, `damaged`, `rejected` and `outstanding` strings; its status is `awaiting`, `partial` or `complete`. The original PR status remains approved and its estimate is unchanged. GET PR detail/register supplies authorized receipt history; no separate receipt mutation endpoint exists.

Migration `004_receipts.sql` adds immutable receipts. Earlier applied migrations are unchanged. `receiving.py` owns receipt calculations and replacement validation; `workflow.py` owns the common transaction, permissions, locks, retry replay and audit. A shared PR row lock serializes receipt and revision commands; stale commands get a conflict and must refresh. Identical-key/body retries return the saved result. Different command keys represent new receiving actions; delivery-reference deduplication is not implemented.

## Conservative revision rules in this slice

After any receipt/acceptance record exists, keep the purchase type, supplier, existing line order and descriptions. New scope can be appended; quantities may change if they stay at or above already accepted amounts. Existing lines cannot be removed. This preserves durable line references without migrating historical PO snapshots to a new line-ID model; it is deliberately stricter than a future amendment model could be. For a different counterparty/type or changed item identity, create a separate PR.

These checks run when proposing, approving and issuing a revision. They also protect an order first received after a proposal was approved. Historical receipt snapshots retain original prices even if an approved future revision changes prices. Invoice-aware amendment rules will be designed with the invoice slice.

## Verification and remaining limits

All 54 backend tests passed against isolated real PostgreSQL schemas. Receiving cases cover partial and multiple receipts, whole service milestones, role/CSRF/state/version checks, quantity and line validation, pending-change limits, original snapshot preservation, revalidation after approval, approved-proposal return, appended new lines, idempotent replay, competing receipt commands, audit-failure rollback and database immutability. Application recreation also preserves full records.

`tools/check-receiving.cjs` verifies the real browser flow: Dinesh receives during a pending change, a combined quantity overflow fails without a write, approved issuance recalculates outstanding, the next receipt references revision 2, reload/history/filter behavior, service acceptance, themes and mobile. Sanitized result: `runtime-results/receiving-browser.json`. API process restart evidence: `runtime-results/receiving-restart.json`.

This slice records confirmations with text evidence references; document uploads, stock movements, supplier returns, correction/reversal, cancellation and receipt edits are not implemented. Receiver mistakes require a future audited correction flow rather than overwriting history. No supplier notification is sent. This is a tested application slice, not completion of the full production-ready milestone or its user code inspection.
