import React, { useState } from "react";
import Button from "@atlaskit/button/new";
import type { PR, User } from "./types";

export const invoiceLabels: Record<string, string> = {
  awaiting_review: "Awaiting invoice review",
  needs_clarification: "Invoice needs clarification",
  reviewed: "Invoice reviewed",
  rejected: "Invoice rejected",
};
const myr = (value: string) =>
  new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR" }).format(
    Number(value),
  );

export function InvoiceForm({
  record,
  busy,
  onSave,
  onCancel,
}: {
  record: PR;
  busy: boolean;
  onSave: (body: object) => Promise<void>;
  onCancel: () => void;
}) {
  const [revision, setRevision] = useState(record.purchase_order!.revision);
  const order = record.po_history.find((po) => po.revision === revision)!;
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const lines = order.snapshot.items
      .map((_, index) => ({
        line_index: index,
        quantity: String(form.get(`quantity_${index}`) || "0"),
        unit_price: String(form.get(`price_${index}`)),
      }))
      .filter((line) => Number(line.quantity) > 0);
    await onSave({
      po_revision: revision,
      supplier: form.get("supplier"),
      invoice_number: form.get("invoice_number"),
      invoice_date: form.get("invoice_date"),
      evidence_reference: form.get("evidence_reference"),
      receipt_ids: form.getAll("receipt_ids"),
      lines,
    });
  }
  return (
    <form className="request-form" onSubmit={save}>
      <h2>Capture supplier invoice</h2>
      <p>
        Capture the supplier’s actual billed quantities and prices, even if
        delivery is incomplete. Amounts are MYR line totals; tax, freight and
        credit notes are outside this slice.
      </p>
      <label htmlFor="invoice-po-revision">Issued PO revision</label>
      <select
        id="invoice-po-revision"
        value={revision}
        onChange={(e) => setRevision(Number(e.target.value))}
      >
        {record.po_history.map((po) => (
          <option key={po.revision} value={po.revision}>
            {po.number} · Revision {po.revision}
          </option>
        ))}
      </select>
      <label>
        Supplier invoice number
        <input name="invoice_number" required minLength={1} maxLength={100} />
      </label>
      <label>
        Invoice date
        <input name="invoice_date" required type="date" />
      </label>
      <label>
        Invoice evidence reference
        <input
          name="evidence_reference"
          required
          minLength={2}
          maxLength={300}
        />
      </label>
      <p className="muted">
        Use a document filename or reference. Uploads will follow with document
        ingestion.
      </p>
      <div key={revision}>
        <label>
          Billed supplier
          <input
            name="supplier"
            required
            minLength={2}
            maxLength={150}
            defaultValue={order.snapshot.supplier}
          />
        </label>
        {order.snapshot.items.map((line, index) => (
          <fieldset key={index}>
            <legend>
              Line {index + 1} · {line.description}
            </legend>
            <p>
              Linked PO: {line.quantity} × MYR {line.unit_price}
            </p>
            <div className="form-grid">
              <label>
                Invoice quantity, line {index + 1}
                <input
                  name={`quantity_${index}`}
                  type="number"
                  min="0"
                  max="100000"
                  step={order.snapshot.kind === "service" ? "1" : "0.01"}
                  defaultValue="0"
                  required
                />
              </label>
              <label>
                Invoice unit price, line {index + 1} (MYR)
                <input
                  name={`price_${index}`}
                  type="number"
                  min="0.01"
                  max="1000000"
                  step="0.01"
                  defaultValue={line.unit_price}
                  required
                />
              </label>
            </div>
          </fieldset>
        ))}
      </div>
      <fieldset>
        <legend>Receipt evidence (optional)</legend>
        {record.receipts.length ? (
          record.receipts.map((receipt) => (
            <label className="evidence-choice" key={receipt.id}>
              <input type="checkbox" name="receipt_ids" value={receipt.id} />
              {receipt.number} · PO revision {receipt.po_revision} ·{" "}
              {receipt.reference}
            </label>
          ))
        ) : (
          <p>No receipts yet. You can capture the invoice now.</p>
        )}
      </fieldset>
      <div className="actions form-footer">
        <Button appearance="primary" type="submit" isDisabled={busy}>
          {busy ? "Capturing…" : "Capture invoice"}
        </Button>
        <Button type="button" onClick={onCancel} isDisabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function InvoicePanel({
  record,
  user,
  busy,
  onCapture,
  onReview,
}: {
  record: PR;
  user: User;
  busy: boolean;
  onCapture: () => void;
  onReview: (body: object) => Promise<void>;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [outcome, setOutcome] = useState("reviewed");
  const [reason, setReason] = useState("");
  if (!record.purchase_order) return null;
  const awaiting = record.invoices.filter((invoice) =>
    ["awaiting_review", "needs_clarification"].includes(invoice.status),
  );
  return (
    <section className="invoice-panel" aria-label="Supplier invoices">
      <div className="eyebrow">Independent invoice review</div>
      <h3>Supplier invoices · {record.invoices.length}</h3>
      <p>
        {awaiting.length
          ? `${awaiting.length} invoice(s) need Eva’s attention.`
          : record.invoices.length
            ? "No invoices awaiting review."
            : "Invoice capture is available before full delivery."}{" "}
        Reviewing an invoice leaves outstanding deliveries open and does not
        authorize payment.
      </p>
      {user.role === "invoice_reviewer" && (
        <Button appearance="primary" isDisabled={busy} onClick={onCapture}>
          Capture supplier invoice
        </Button>
      )}
      {user.role === "invoice_reviewer" && awaiting.length > 0 && (
        <div className="actions invoice-next-actions">
          {awaiting.map((invoice) => (
            <Button
              key={invoice.id}
              appearance="primary"
              isDisabled={busy}
              onClick={() => {
                setSelected(invoice.id);
                setOutcome("reviewed");
                setReason("");
                requestAnimationFrame(() => {
                  const target = document.getElementById(
                    `invoice-${invoice.id}`,
                  );
                  target?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
                  target?.focus({ preventScroll: true });
                });
              }}
            >
              Review invoice {invoice.invoice_number}
            </Button>
          ))}
        </div>
      )}
      {record.invoices.map((invoice) => {
        const checks = record.invoice_checks[invoice.id];
        const reviewable = ["awaiting_review", "needs_clarification"].includes(
          invoice.status,
        );
        return (
          <details
            className="proposal-card"
            id={`invoice-${invoice.id}`}
            tabIndex={-1}
            key={invoice.id}
            open={selected === invoice.id ? true : undefined}
          >
            <summary>
              {invoice.invoice_number} · {invoiceLabels[invoice.status]} ·{" "}
              {myr(invoice.total)}
            </summary>
            <p>
              {invoice.number} · {invoice.supplier} · Invoice date{" "}
              {invoice.invoice_date}
              <br />
              Captured by {invoice.recorded_by} ·{" "}
              {new Date(invoice.recorded_at).toLocaleString("en-MY")}
              <br />
              Linked PO revision {invoice.po_revision} · Evidence:{" "}
              {invoice.evidence_reference}
            </p>
            <p>
              Receipt evidence:{" "}
              {invoice.receipt_evidence.length
                ? invoice.receipt_evidence
                    .map((r) => `${r.number} (revision ${r.po_revision})`)
                    .join(", ")
                : "None linked at capture"}
            </p>
            <h4>Review checks · advisory</h4>
            <p className="muted">{checks.basis}</p>
            {checks.warnings.length ? (
              <ul className="invoice-warnings">
                {checks.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : (
              <p>
                No differences found by these limited quantity/price checks.
              </p>
            )}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Line</th>
                    <th>Billed qty</th>
                    <th>Billed unit MYR</th>
                    <th>PO unit MYR</th>
                    <th>Accepted</th>
                    <th>Combined billed qty*</th>
                  </tr>
                </thead>
                <tbody>
                  {checks.lines.map((line) => (
                    <tr key={line.line_index}>
                      <td>{line.description}</td>
                      <td>{line.invoiced}</td>
                      <td>{line.invoice_unit_price}</td>
                      <td>{line.po_unit_price}</td>
                      <td>{line.accepted}</td>
                      <td>{line.combined_claimed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <small>
              *All non-rejected invoices for the same supplier, purchase type
              and line identity. Rejected claims remain in history.
            </small>
            {user.role === "invoice_reviewer" && reviewable && (
              <>
                {selected === invoice.id && (
                  <form
                    className="invoice-review-form"
                    onSubmit={async (e) => {
                      e.preventDefault();
                      await onReview({
                        invoice_id: invoice.id,
                        outcome,
                        reason,
                      });
                    }}
                  >
                    <label htmlFor="invoice-review-outcome">
                      Review outcome
                    </label>
                    <select
                      id="invoice-review-outcome"
                      value={outcome}
                      onChange={(e) => setOutcome(e.target.value)}
                    >
                      <option value="reviewed">Reviewed</option>
                      <option value="needs_clarification">
                        Needs clarification
                      </option>
                      <option value="rejected">Rejected</option>
                    </select>
                    <label htmlFor="invoice-review-reason">Review reason</label>
                    <textarea
                      id="invoice-review-reason"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      minLength={1}
                      maxLength={2000}
                      required
                    />
                    <p className="muted">
                      Record your findings, including any differences. Reviewed
                      is a review record, not a payment or reconciliation
                      approval. Captured fields remain unchanged; clarification
                      findings can be recorded in a follow-up review.
                    </p>
                    <Button
                      type="submit"
                      appearance="primary"
                      isDisabled={busy || !reason.trim()}
                    >
                      Record invoice outcome
                    </Button>
                  </form>
                )}
              </>
            )}
            {invoice.reviews.length > 0 && (
              <>
                <h4>Review history</h4>
                <ol className="activity">
                  {invoice.reviews.map((review, index) => (
                    <li key={index}>
                      <strong>
                        {review.actor} · {invoiceLabels[review.outcome]}
                      </strong>
                      <p>{review.reason}</p>
                      <small>
                        {new Date(review.created_at).toLocaleString("en-MY")} ·{" "}
                        {review.checks.warnings.length} advisory difference(s)
                        at review time
                      </small>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </details>
        );
      })}
    </section>
  );
}
