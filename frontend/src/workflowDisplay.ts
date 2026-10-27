import type { PR } from "./types";

// Display the team's current handoff while preserving the PR's approved state.
export const statuses: Record<string, string> = {
  draft: "Draft",
  submitted: "Awaiting PR approval",
  returned: "PR returned for changes",
  approved: "PR approved · Ready for PO",
  po_pending: "Awaiting PO approval",
  po_approved: "PO approved · Ready to issue",
  po_returned: "PO returned for changes",
  po_issued: "PO issued · Awaiting receipt",
  po_partial: "PO partially fulfilled",
  po_complete: "PO fulfilled",
};

export function workflowStatus(record: PR): string {
  if (record.status !== "approved") return record.status;
  const proposal = record.po_proposals.find((p) =>
    ["pending", "approved"].includes(p.status),
  );
  if (proposal)
    return proposal.status === "pending" ? "po_pending" : "po_approved";
  if (record.po_proposals[0]?.status === "returned") return "po_returned";
  return record.purchase_order
    ? record.fulfilment?.status === "complete"
      ? "po_complete"
      : record.fulfilment?.status === "partial"
        ? "po_partial"
        : "po_issued"
    : "approved";
}

export function nextStep(record: PR): { owner: string; action: string } {
  const state = workflowStatus(record);
  switch (state) {
    case "submitted":
      return { owner: "Ben · Approver", action: "Review PR" };
    case "po_pending":
      return { owner: "Ben · Approver", action: "Review PO proposal" };
    case "po_approved":
      return { owner: "Chloe · Buyer", action: "Issue approved PO terms" };
    case "po_returned":
      return {
        owner: "Chloe · Buyer",
        action: "Revise and resubmit PO proposal",
      };
    case "approved":
      return { owner: "Chloe · Buyer", action: "Prepare PO" };
    case "po_complete":
      return {
        owner: "Eva · Invoice reviewer",
        action: "Capture or review supplier invoices",
      };
    case "po_partial":
    case "po_issued":
      return {
        owner: "Dinesh · Receiver / service acceptor",
        action:
          record.purchase_order?.snapshot.kind === "service"
            ? "Service acceptance"
            : "Goods receipt",
      };
    default:
      return {
        owner: `${record.owner_id === "aina" ? "Aina" : record.owner_id} · Requester`,
        action:
          state === "returned"
            ? "Edit and resubmit PR"
            : "Complete and submit PR",
      };
  }
}
