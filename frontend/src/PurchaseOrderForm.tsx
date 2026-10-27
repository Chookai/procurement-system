import React from "react";
import Button from "@atlaskit/button/new";
import type { PR } from "./types";

export function PurchaseOrderForm({
  record,
  busy,
  onIssue,
  onCancel,
}: {
  record: PR;
  busy: boolean;
  onIssue: (body: object) => Promise<void>;
  onCancel: () => void;
}) {
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await onIssue({
      supplier: String(form.get("supplier")),
      delivery_terms: String(form.get("delivery_terms")),
      unit_prices: record.items.map((_, i) =>
        String(form.get(`unit_price_${i}`)),
      ),
    });
  }
  return (
    <form className="request-form" onSubmit={submit}>
      <div className="eyebrow">
        {record.number} · approved version {record.version}
      </div>
      <h2>Prepare purchase order</h2>
      <p className="muted">
        Confirm the supplier and final line prices. Issuing creates a permanent
        snapshot; it does not send an email or supplier order externally.
      </p>
      <label htmlFor="po-supplier">Confirmed supplier</label>
      <input
        id="po-supplier"
        name="supplier"
        required
        minLength={2}
        maxLength={150}
        defaultValue={record.supplier_suggestion}
      />
      <h3>Approved scope</h3>
      <p>
        {record.title} · {record.vessel} · {record.location}
      </p>
      {record.items.map((line, i) => (
        <fieldset key={i}>
          <legend>Line {i + 1}</legend>
          <strong>{line.description}</strong>
          <p>
            Approved quantity: {line.quantity}{" "}
            {record.kind === "service" ? "milestones" : "units"}
          </p>
          <label htmlFor={`po-price-${i}`}>
            Final unit price, line {i + 1} (MYR)
          </label>
          <input
            id={`po-price-${i}`}
            name={`unit_price_${i}`}
            type="number"
            required
            min="0.01"
            max={line.unit_price}
            step="0.01"
            defaultValue={line.unit_price}
          />
          <small>
            Approved unit estimate: MYR {line.unit_price}. Increases require
            reapproval. Cancel and choose Propose PO terms to request a change.
          </small>
        </fieldset>
      ))}
      <label htmlFor="po-delivery">Delivery terms (optional)</label>
      <textarea id="po-delivery" name="delivery_terms" maxLength={2000} />
      <div className="actions form-footer">
        <Button appearance="primary" type="submit" isDisabled={busy}>
          {busy ? "Issuing…" : "Issue PO"}
        </Button>
        <Button type="button" onClick={onCancel} isDisabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
