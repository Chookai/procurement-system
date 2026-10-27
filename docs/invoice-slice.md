# Supplier invoice capture and human review

Implemented 26 October 2026 for the local mocked procurement application. PR, PO, receiving and invoice review now form the structured workflow; real ingestion, agent tools/retrieval and RAG evaluations remain pending. This is not a production-readiness or full-milestone completion claim.

## Try as Eva

Sign in as `eva` with the local demo password `harbor-demo`. Choose an issued PO; invoices can arrive before any receipt or before delivery is complete. Eva’s invoice panel appears before fulfilment details so capture/review actions are visible.

1. Choose **Capture supplier invoice**. Select an issued revision; enter the supplier invoice number/date, billed supplier, invoice evidence filename/reference, actual quantities/prices, and optional receipt evidence links.
2. Capture. The MYR total is calculated on the backend using per-line decimal rounding. Invoice capture does not change ordered, accepted or outstanding quantities.
3. Use the visible **Review invoice [number]** action. Inspect captured facts, linked evidence and advisory checks. Choose **Reviewed**, **Needs clarification** or **Rejected** and give a reason.
4. Read the review history. Needs clarification permits a follow-up review after obtaining clarification; reviewed/rejected are final outcomes in this slice. Captured fields and previous review events stay immutable.
5. Use **Filter by invoice review** to find requests containing an invoice in the selected state. Register rows show invoice counts/outcomes and Eva’s action separately from fulfilment and PO change status.

Canonical example: ten pump seals ordered at MYR 200; six accepted; capture and review six × MYR 200 = MYR 1,200. Four remain outstanding. Nothing is paid or formally reconciled. Multiple invoices can reference the same PO.

## What the checks mean

The screen compares billed supplier/line price/quantity with the linked issued snapshot, equivalent accepted quantities and combined non-rejected invoice quantities. It warns about supplier/price differences, billing beyond ordered or accepted quantities and overlapping aggregate claims. Capturing a discrepancy is allowed so Eva can investigate the actual supplier claim. **Reviewed records Eva’s examination; it does not certify that every difference is resolved or authorize payment.** A reason is required for all outcomes, including when Eva records reviewed with differences.

Current accepted/combined-claim figures are recalculated for the same PO, supplier, purchase type, line position and description. They are not allocations of receipts to invoices. Optional receipt evidence links preserve chosen documents at capture; their quantities are not a formal matched allocation. Each review freezes its then-current check results so later deliveries, invoices or rejections cannot rewrite what Eva saw.

Historical PO revisions can be selected. If historical scope differs from current scope, it gets a warning rather than silently treating new-item receipts as evidence for the old invoice. The invoice stores the selected original terms and receipt snapshots; changes to the current PO do not reprice captured invoices.

## Code walkthrough

```text
Invoices.tsx: InvoiceForm
  capture actual billed facts + optional receipt IDs
main.tsx: invoiceCommand()
  POST /requisitions/{id}/invoices
app.py + contracts.py
  signed identity + CSRF + body validation + idempotency key
workflow.command()
  Eva's role; approved parent; current command version; PR row lock
invoicing.invoice_command()
  require an issued revision; validate line and receipt references
  INSERT immutable supplier invoice + original evidence
workflow.command()
  advance PR version + audit + saved retry response; commit together

Invoices.tsx: InvoicePanel
  POST /requisitions/{id}/invoices/review
invoicing.invoice_command()
  find invoice on this PO; require open/clarification state
  snapshot advisory checks; append reasoned review event
  same shared transaction and audit boundary
```

`amounts.py` now owns the decimal line-total calculation shared by PR/PO and invoice amounts. `receiving.py` continues to own accepted/outstanding calculations. The common transaction, permissions, command replay and audit remain in `workflow.py`; invoice-specific rules live in `invoicing.py`.

Migration `005_invoices.sql` adds immutable invoices and append-only invoice review events. A unique constraint covers normalized billed supplier + supplier invoice number across the local company, including different POs. Normalization collapses whitespace and ignores case. Identical-key/body retries replay their original response; a new capture of an existing supplier invoice returns a conflict. This is a demo text-based supplier identity, not a master supplier registry or a guarantee against every spelling/punctuation variation.

## HTTP contract

All paths start with `/api/v1/requisitions/{id}`. Both commands require the signed session, `X-CSRF-Token`, `Idempotency-Key` and current `expected_version`. Both are limited to the invoice reviewer role.

| Command | Additional fields |
|---|---|
| POST `/invoices` | `po_revision`, `supplier`, `invoice_number`, `invoice_date`, `evidence_reference`, optional `receipt_ids`, `lines` with `line_index`, positive `quantity` and `unit_price` |
| POST `/invoices/review` | `invoice_id`, `outcome` (`reviewed`, `needs_clarification`, `rejected`), nonblank `reason` |

At least one invoice line is required. Service quantities use whole milestones. Lines and receipt references must be unique, and receipt evidence must belong to this PO. Quantities/prices support two decimal places within the existing field limits. Unknown fields, including payment flags, are rejected.

Authorized PR detail/register responses include `invoices` and `invoice_checks`. Invoice state is derived from its latest review event, starting at `awaiting_review`. There is no invoice edit/delete/payment endpoint. A reviewed or rejected outcome cannot be overwritten; a clarification outcome can be followed by a new reasoned review. An invoice ID from another PO cannot be reviewed through this parent.

## Interaction with PO amendments

Once invoice evidence exists, replacement proposals must preserve current supplier, goods/service type, existing line order and descriptions; new lines may be appended. This conservative rule preserves references even when invoicing precedes receiving. The guard runs at proposal, approval and issuance, including when an invoice arrived after approval. Receipt-based accepted-quantity floors remain enforced independently.

Invoice quantities are supplier claims; this slice does not turn those claims or a reviewed label into a hard payable balance or a formal reconciliation rule. Credit/cancellation and financial amendment constraints remain later work.

## Verification and limits

All 75 backend tests passed against isolated real PostgreSQL schemas. New tests cover the ten/six/MYR 1,200/four journey, pre-receipt capture, multiple invoices/all outcomes, clarification follow-up, frozen review evidence, historical-scope differences, service quantities, exact decimal totals, duplicate protection/retry replay, roles/CSRF/state/reference boundaries, competing reviews, rollback/retry after injected audit failure, database immutability and application recreation.

`tools/check-invoices.cjs` exercises actual Eva browser capture/review, receipt links, all outcomes, advisory warnings, duplicate rejection, independent fulfilment, review filter, reload, themes and 390px layout. Sanitized results are `runtime-results/invoices-browser.json` and `runtime-results/application-tests.xml`. Actual API process restart is recorded in `runtime-results/invoices-restart.json`.

Amounts currently include line totals only; tax, freight, discounts, credit notes and negative invoices are not modeled. Evidence is a text reference and saved structured links; binary upload/parsing comes with ingestion. Commercial corrections/resubmission of captured fields and reopening final outcomes require a future version/correction design. Formal reconciliation, payment execution, accounting postings and automatic financial authorization are explicitly outside this slice. User code inspection and the real RAG/evaluation gates remain required before the full milestone can close.

## Selected-PR display fix · 27 October 2026

Switching from PR-0014 to PR-0013 reproduced stale invoice DOM entries: five entries appeared although PR-0013 had one invoice. The invoice panel and PO review panel used the same sibling React key, producing duplicate-key warnings and unsupported reconciliation behavior. Their keys now include distinct panel namespaces. Selecting another PR also clears notices/errors from the previous selection. Business records were unchanged.

`tools/check-selected-pr.cjs` is the regression command (pass the installed Playwright module path as its first argument when needed). It repeatedly switches the two screenshot PRs, checks invoice identities/counts, PO/receipt/activity history and unsaved review state across Eva, Ben, Chloe and Dinesh, and rejects duplicate-key warnings. It also checks light/dark and 390px layout. Result: `runtime-results/selected-pr-browser.json`. A full browser refresh clears any DOM left over from the earlier development session.
