import React, { useState } from "react";
import Button from "@atlaskit/button/new";
import type { PR, User, PurchaseOrder } from "./types";

function Terms({ snapshot }: { snapshot: PurchaseOrder["snapshot"] }) {
  return (
    <>
      <p>
        <strong>{snapshot.title}</strong> · {snapshot.kind}
        <br />
        {snapshot.vessel} · {snapshot.location} · Due {snapshot.required_date}
      </p>
      <p>{snapshot.purpose}</p>
      <p>
        Supplier: <strong>{snapshot.supplier}</strong>
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Scope</th>
              <th>Qty</th>
              <th>Unit MYR</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.items.map((line, i) => (
              <tr key={i}>
                <td>{line.description}</td>
                <td>{line.quantity}</td>
                <td>{line.unit_price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>Delivery terms: {snapshot.delivery_terms || "None recorded"}</p>
    </>
  );
}

export function POActionBar({
  record,
  user,
  busy,
  onPropose,
  onPrepare,
}: {
  record: PR;
  user: User;
  busy: boolean;
  onPropose: () => void;
  onPrepare: () => void;
}) {
  const proposal = record.po_proposals.find((p) =>
    ["pending", "approved"].includes(p.status),
  );
  const pending = proposal?.status === "pending";
  const canReview =
    pending &&
    user.role === "approver" &&
    user.id !== proposal.proposed_by &&
    user.id !== record.owner_id;
  const buyer = user.role === "buyer";
  function review() {
    const section = document.getElementById("po-review");
    section?.scrollIntoView({ behavior: "smooth", block: "start" });
    section?.focus({ preventScroll: true });
  }
  return (
    <section className="po-action-bar" aria-label="Next procurement action">
      <div className="eyebrow">
        {proposal
          ? "Next step"
          : record.purchase_order
            ? "Purchase order"
            : "Ready for purchase order"}
      </div>
      <strong>
        {proposal
          ? pending
            ? "Awaiting Ben’s approval"
            : "Approved · Chloe can issue the changed terms"
          : record.purchase_order
            ? `${record.purchase_order.number} · Revision ${record.purchase_order.revision} issued`
            : "PR approved · Chloe can prepare the PO"}
      </strong>
      <p>
        {proposal
          ? "Current issued terms stay active until the approved proposal is issued."
          : record.purchase_order
            ? "Need to change the supplier, scope or price? Chloe can propose a revision for Ben to approve."
            : "Prepare the order, or request approval for changed scope or higher prices."}
      </p>
      <div className="actions">
        {!proposal && buyer && (
          <>
            <Button
              appearance="primary"
              isDisabled={busy}
              onClick={record.purchase_order ? onPropose : onPrepare}
            >
              {record.purchase_order ? "Revise PO" : "Prepare PO"}
            </Button>
            {!record.purchase_order && (
              <Button isDisabled={busy} onClick={onPropose}>
                Propose changed terms
              </Button>
            )}
          </>
        )}
        {proposal && (
          <Button
            appearance={
              canReview || (!pending && buyer) ? "primary" : "default"
            }
            isDisabled={busy}
            onClick={review}
          >
            {canReview
              ? "Review PO proposal"
              : !pending && buyer
                ? "Review and issue approved terms"
                : "View PO proposal"}
          </Button>
        )}
      </div>
      {!proposal && !buyer && (
        <small>
          Signed in as {user.name}. PO changes are started by Chloe, the
          procurement buyer.
        </small>
      )}
    </section>
  );
}

export function POReview({
  record,
  user,
  busy,
  onAction,
}: {
  record: PR;
  user: User;
  busy: boolean;
  onAction: (action: string, id: string, reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const open = record.po_proposals.find((p) =>
    ["pending", "approved"].includes(p.status),
  );
  return (
    <section
      id="po-review"
      tabIndex={-1}
      className="issued-order"
      aria-label="PO revisions and reapproval"
    >
      <h3>PO revisions and reapproval</h3>
      <p className="muted">
        Ben reviews every proposed change. Approval alone leaves the current
        issued PO active; Chloe must issue the approved terms.
      </p>
      {record.po_proposals.map((proposal) => (
        <details
          key={proposal.id}
          open={proposal === open ? true : undefined}
          className="proposal-card"
        >
          <summary>
            Proposal · {proposal.status} · MYR {proposal.total_myr}
          </summary>
          <p>
            {proposal.proposed_by} ·{" "}
            {new Date(proposal.created_at).toLocaleString("en-MY")} · Based on{" "}
            {proposal.base_revision
              ? `revision ${proposal.base_revision}`
              : "approved PR (first issuance)"}
          </p>
          <p>
            <strong>Reason:</strong> {proposal.reason}
          </p>
          <Terms snapshot={proposal.snapshot} />
          {proposal.decided_by && (
            <p>
              Decision: {proposal.decided_by} ·{" "}
              {new Date(proposal.decided_at!).toLocaleString("en-MY")}{" "}
              {proposal.decision_reason}
            </p>
          )}
          {["pending", "approved"].includes(proposal.status) &&
            user.role === "approver" &&
            user.id !== proposal.proposed_by &&
            user.id !== record.owner_id && (
              <>
                <label>
                  Return reason
                  <textarea
                    value={reason}
                    maxLength={1000}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                <div className="actions">
                  {proposal.status === "pending" && (
                    <Button
                      appearance="primary"
                      isDisabled={busy}
                      onClick={() => onAction("approve", proposal.id, "")}
                    >
                      Approve PO terms
                    </Button>
                  )}
                  <Button
                    isDisabled={busy || !reason.trim()}
                    onClick={async () => {
                      await onAction("return", proposal.id, reason);
                      setReason("");
                    }}
                  >
                    Return PO proposal
                  </Button>
                </div>
              </>
            )}
          {proposal.status === "approved" && user.role === "buyer" && (
            <Button
              appearance="primary"
              isDisabled={busy}
              onClick={() => onAction("issue", proposal.id, "")}
            >
              Issue approved PO terms
            </Button>
          )}
        </details>
      ))}
      {record.po_history.length > 0 && (
        <>
          <h3>Issued history</h3>
          {[...record.po_history].reverse().map((order) => (
            <details key={order.revision} className="proposal-card">
              <summary>
                {order.number} · revision {order.revision} · MYR {order.total}
                {order.revision === record.purchase_order?.revision
                  ? " · Current"
                  : " · Superseded"}
              </summary>
              <p>
                Issued by {order.issued_by} ·{" "}
                {new Date(order.issued_at).toLocaleString("en-MY")}
              </p>
              <Terms snapshot={order.snapshot} />
            </details>
          ))}
        </>
      )}
    </section>
  );
}
