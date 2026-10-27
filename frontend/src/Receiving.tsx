import React from "react";
import Button from "@atlaskit/button/new";
import type { PR, User } from "./types";

export const fulfilmentLabels = {
  awaiting: "Awaiting receipt / acceptance",
  partial: "Partially received / accepted",
  complete: "Fully received / accepted",
};

export function fulfilmentLabel(record: PR) {
  const summary = record.fulfilment;
  if (!summary) return "";
  return summary.kind === "service"
    ? {
        awaiting: "Awaiting service acceptance",
        partial: "Partially accepted",
        complete: "Fully accepted",
      }[summary.status]
    : {
        awaiting: "Awaiting goods receipt",
        partial: "Partially received",
        complete: "Fully received",
      }[summary.status];
}

export function ReceivingPanel({
  record,
  user,
  busy,
  onReceive,
}: {
  record: PR;
  user: User;
  busy: boolean;
  onReceive: () => void;
}) {
  const summary = record.fulfilment;
  if (!summary || !record.purchase_order) return null;
  const service = summary.kind === "service";
  const changing = record.po_proposals.some((p) =>
    ["pending", "approved"].includes(p.status),
  );
  return (
    <section className="receiving-panel" aria-label="Issued PO fulfilment">
      <div className="eyebrow">
        Current issued PO · Revision {summary.po_revision}
      </div>
      <h3>
        {service ? "Service acceptance" : "Goods receipt"} ·{" "}
        {summary.status === "complete"
          ? service
            ? "Fully accepted"
            : "Fully received"
          : summary.status === "partial"
            ? "Partially accepted"
            : "Awaiting acceptance"}
      </h3>
      {changing && (
        <p className="receiving-warning">
          PO change in progress. Receive only against issued revision{" "}
          {summary.po_revision}; proposed quantities are not available for
          receiving.
        </p>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Issued line</th>
              <th>Ordered</th>
              <th>Accepted</th>
              <th>Damaged</th>
              <th>Rejected</th>
              <th>Outstanding</th>
            </tr>
          </thead>
          <tbody>
            {summary.lines.map((line) => (
              <tr key={line.line_index}>
                <td>{line.description}</td>
                <td>{line.ordered}</td>
                <td>{line.accepted}</td>
                <td>{line.damaged}</td>
                <td>{line.rejected}</td>
                <td>
                  <strong>{line.outstanding}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        Only accepted quantities fulfil the order. Damaged and rejected totals
        remain in the inspection history.
      </p>
      {summary.status !== "complete" && (
        <>
          <small>
            Next: Dinesh ·{" "}
            {service
              ? "Confirm completed milestones"
              : "Record delivered goods"}
          </small>
          {user.role === "receiver" && (
            <Button appearance="primary" isDisabled={busy} onClick={onReceive}>
              {service ? "Record service acceptance" : "Record goods receipt"}
            </Button>
          )}
        </>
      )}
      {summary.status === "complete" && (
        <p>
          All issued quantities are accepted. Invoice review remains separate.
        </p>
      )}
    </section>
  );
}

export function ReceiptForm({
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
  const summary = record.fulfilment!;
  const service = summary.kind === "service";
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const lines = summary.lines
      .map((line) => ({
        line_index: line.line_index,
        accepted: String(form.get(`accepted_${line.line_index}`) || "0"),
        damaged: String(form.get(`damaged_${line.line_index}`) || "0"),
        rejected: String(form.get(`rejected_${line.line_index}`) || "0"),
      }))
      .filter((line) =>
        [line.accepted, line.damaged, line.rejected].some((q) => Number(q) > 0),
      );
    await onSave({
      po_revision: summary.po_revision,
      received_on: form.get("received_on"),
      reference: form.get("reference"),
      notes: form.get("notes"),
      lines,
    });
  }
  const today = new Date();
  const date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return (
    <form className="request-form" onSubmit={save}>
      <div className="eyebrow">
        {record.purchase_order!.number} · Issued revision {summary.po_revision}
      </div>
      <h2>{service ? "Record service acceptance" : "Record goods receipt"}</h2>
      <p>
        Record what was inspected. Accepted, damaged and rejected quantities for
        each line must total no more than its outstanding quantity. Leave
        untouched lines at zero.
      </p>
      <label>
        Received / inspected on
        <input name="received_on" type="date" required defaultValue={date} />
      </label>
      <label>
        {service ? "Work completion reference" : "Delivery note reference"}
        <input name="reference" required minLength={2} maxLength={150} />
      </label>
      {summary.lines
        .filter((line) => Number(line.outstanding) > 0)
        .map((line) => (
          <fieldset key={line.line_index}>
            <legend>
              Line {line.line_index + 1} · {line.description}
            </legend>
            <p>
              Ordered {line.ordered} · Accepted {line.accepted} · Outstanding{" "}
              <strong>{line.outstanding}</strong>
            </p>
            <div className="form-grid">
              <label>
                Accepted, line {line.line_index + 1}
                <input
                  type="number"
                  name={`accepted_${line.line_index}`}
                  required
                  min="0"
                  max={line.outstanding}
                  step={service ? "1" : "0.01"}
                  defaultValue="0"
                />
              </label>
              {!service && (
                <label>
                  Damaged, line {line.line_index + 1}
                  <input
                    type="number"
                    name={`damaged_${line.line_index}`}
                    required
                    min="0"
                    max={line.outstanding}
                    step="0.01"
                    defaultValue="0"
                  />
                </label>
              )}
              <label>
                Rejected, line {line.line_index + 1}
                <input
                  type="number"
                  name={`rejected_${line.line_index}`}
                  required
                  min="0"
                  max={line.outstanding}
                  step={service ? "1" : "0.01"}
                  defaultValue="0"
                />
              </label>
            </div>
          </fieldset>
        ))}
      <label>
        Inspection notes
        <textarea name="notes" maxLength={2000} />
      </label>
      <p className="muted">
        Notes are required for any damaged or rejected quantities. Service
        acceptance uses whole milestones.
      </p>
      <div className="actions form-footer">
        <Button appearance="primary" type="submit" isDisabled={busy}>
          {busy
            ? "Recording…"
            : service
              ? "Confirm service acceptance"
              : "Confirm goods receipt"}
        </Button>
        <Button isDisabled={busy} onClick={onCancel} type="button">
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function ReceiptHistory({ record }: { record: PR }) {
  if (!record.receipts.length) return null;
  return (
    <section
      aria-label="Receipt and acceptance history"
      className="issued-order"
    >
      <h3>Receipt and acceptance history</h3>
      {[...record.receipts].reverse().map((receipt) => (
        <details className="proposal-card" key={receipt.id}>
          <summary>
            {receipt.number} ·{" "}
            {receipt.kind === "goods" ? "Goods receipt" : "Service acceptance"}{" "}
            · PO revision {receipt.po_revision}
          </summary>
          <p>
            {receipt.recorded_by} ·{" "}
            {new Date(receipt.recorded_at).toLocaleString("en-MY")}
            <br />
            Received / inspected: {receipt.received_on}
            <br />
            Reference: {receipt.reference}
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Recorded line</th>
                  <th>Accepted</th>
                  <th>Damaged</th>
                  <th>Rejected</th>
                </tr>
              </thead>
              <tbody>
                {receipt.lines.map((line) => (
                  <tr key={line.line_index}>
                    <td>
                      {receipt.po_snapshot.items[line.line_index].description}
                    </td>
                    <td>{line.accepted}</td>
                    <td>{line.damaged}</td>
                    <td>{line.rejected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>{receipt.notes}</p>
          <p className="muted">
            Terms recorded with this receipt: {receipt.po_snapshot.supplier}.
            Original quantities and prices stay linked to issued revision{" "}
            {receipt.po_revision}.
          </p>
        </details>
      ))}
    </section>
  );
}
