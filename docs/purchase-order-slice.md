# Historical initial PO slice

Revision and reapproval are now implemented; see [current revision walkthrough](po-revision-slice.md). The initial direct-issuance behavior below is preserved.

# Purchase order issuance slice

Scope: issue the first PO from an approved PR and inspect its permanent terms. This extends the real application at http://127.0.0.1:5175/. No supplier email, external integration or payment action occurs.

## Try it

1. Submit a ten-unit PR at MYR 200 each as Aina, then approve it as Ben.
2. Sign in as Chloe (`chloe`, local password `harbor-demo`). Open the approved PR and choose **Prepare PO**.
3. Confirm the supplier and keep or reduce the unit prices; record optional delivery terms.
4. Choose **Issue PO**. Inspect the PO number, supplier, copied scope, issued total, actor/time, approved PR version and activity event. Refresh the page; the PO persists.

For example, a MYR 2,000 PR estimate may produce a MYR 1,900 PO when the ten unit prices are confirmed at MYR 190. The approved PR estimate remains MYR 2,000; the PO snapshot owns the MYR 1,900 issued value. Goods/service kind, descriptions, quantities, vessel, location, purpose and required date come from the approved PR. PR status remains `approved`; issuance is represented by the linked PO rather than erasing approval state.

## Contract and authorization

- `POST /api/v1/requisitions/{id}/purchase-order`: requires the authenticated buyer, CSRF token and idempotency key. Body: `expected_version`, confirmed `supplier`, one `unit_prices` entry per approved line, optional `delivery_terms`. Returns the updated PR including its nested `purchase_order` with HTTP 201.
- `GET /api/v1/purchase-orders/{id}`: returns the stored PO only if the caller may read its parent PR. Unrelated requesters receive 404. There is no PO update/delete API in this slice.
- Only approved PRs can be issued. Stale versions, another existing PO, or a unit price above the corresponding approved estimate produce 409. A malformed price list, nonpositive price, blank supplier or extra scope fields produce 422.
- Scope/quantity changes are not accepted through the issue payload. Final line prices may remain equal or decrease. Increases are blocked until reapproval; the revision/reapproval UI and commands remain pending under PROC-008. This conservative boundary is not a complete reapproval workflow.

## Code flow

```text
PurchaseOrderForm.tsx → App.issueOrder() → api()
  app.py: issue_purchase_order route
    contracts.py: IssuePurchaseOrder
    identity + CSRF dependencies
    workflow.command("issue_po")
      actor/key lock → replay identical successful command, if any
      PR row lock → buyer/state/version/existing-PO checks
      issue_order() → deep-copy approved PR data; apply confirmed prices
      INSERT purchase_orders
      increment PR version + append issuance audit + save retry response
      commit
  refresh() → render stored snapshot
```

All writes occur in one PostgreSQL transaction. The parent PR lock serializes competing issuance; a unique constraint permits only one initial PO per PR. The same successful command key/body replays its original result. A different command cannot issue another PO. Migration `002_purchase_orders.sql` adds the table and a trigger rejecting UPDATE or DELETE of issued rows. Future revisions will need explicit append-only history design and reapproval commands rather than mutating this snapshot.

Frontend types moved from `main.tsx` to `src/types.ts` so the new `PurchaseOrderForm` and existing `App` can share them. This is a small extraction; existing PR form behavior is retained.

## Verification and limits

Real PostgreSQL HTTP tests cover buyer-only issuance, approved-state/version gates, higher-price and scope rejection, exact issued totals, retry replay, duplicate/conflicting commands, competing issuance, source/snapshot independence, database mutation protection, application recreation and unrelated-requester denial. The full suite currently has 29 passing tests; see `runtime-results/application-tests.xml`.

The real browser walkthrough passed the existing PR flow plus Chloe supplier/price confirmation, native price-increase constraint, PO issuance, reload persistence and both themes/mobile layout. A separate actual API process stop/start preserved the identical PO snapshot and signed session. Audit-write failure injection also proved that issuance rolls back and the same key can succeed on retry. See `runtime-results/po-browser.json`, `po-restart.json` and `application-tests.xml`. Issuance is local recording only; it does not transmit an order to a supplier. Revision/reapproval workflows, GR/service acceptance, invoice review, document ingestion and RAG remain pending. The full milestone is not complete.

For the conceptual lesson, open [Lesson 03](../learnings/lessons/0003-purchase-order-snapshots.html).
