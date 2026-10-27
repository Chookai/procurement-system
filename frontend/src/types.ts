export type User = { id: string; name: string; role: string };
export type Auth = { user: User; csrf_token: string };
export type Line = {
  description: string;
  quantity: string;
  unit_price: string;
};
export type PREvent = {
  action: string;
  actor: string;
  version: number;
  created_at: string;
  details: {
    reason?: string;
    purchase_order?: PurchaseOrder;
    invoice?: SupplierInvoice;
  };
};
export type PR = {
  id: string;
  number: string;
  owner_id: string;
  title: string;
  kind: "goods" | "service";
  purpose: string;
  vessel: string;
  location: string;
  required_date: string;
  supplier_suggestion: string;
  items: Line[];
  status: string;
  version: number;
  total: string;
  events: PREvent[];
  purchase_order: PurchaseOrder | null;
  po_history: PurchaseOrder[];
  po_proposals: POProposal[];
  receipts: Receipt[];
  fulfilment: Fulfilment | null;
  invoices: SupplierInvoice[];
  invoice_checks: Record<string, InvoiceChecks>;
};

export type PurchaseOrder = {
  id: string;
  number: string;
  status: "issued";
  revision: number;
  requisition_id: string;
  issued_by: string;
  issued_at: string;
  total: string;
  currency: "MYR";
  snapshot: Pick<
    PR,
    | "title"
    | "kind"
    | "purpose"
    | "vessel"
    | "location"
    | "required_date"
    | "items"
  > & {
    supplier: string;
    delivery_terms: string;
    approved_pr_version?: number;
    source_pr_version?: number;
    pr_number: string;
  };
};

export type POProposal = {
  id: string;
  base_revision: number;
  proposed_by: string;
  created_at: string;
  snapshot: PurchaseOrder["snapshot"];
  total_myr: string;
  reason: string;
  status: "pending" | "approved" | "returned" | "issued";
  decided_by: string | null;
  decided_at: string | null;
  decision_reason: string;
};

export type Receipt = {
  id: string;
  number: string;
  po_revision: number;
  kind: "goods" | "service";
  received_on: string;
  reference: string;
  notes: string;
  recorded_by: string;
  recorded_at: string;
  lines: {
    line_index: number;
    accepted: string;
    damaged: string;
    rejected: string;
  }[];
  po_snapshot: PurchaseOrder["snapshot"];
};
export type Fulfilment = {
  status: "awaiting" | "partial" | "complete";
  po_revision: number;
  kind: "goods" | "service";
  lines: {
    line_index: number;
    description: string;
    ordered: string;
    accepted: string;
    damaged: string;
    rejected: string;
    outstanding: string;
  }[];
};

export type InvoiceChecks = {
  warnings: string[];
  basis: string;
  current_po_revision: number;
  lines: {
    line_index: number;
    description: string;
    invoiced: string;
    invoice_unit_price: string;
    po_unit_price: string;
    linked_ordered: string;
    accepted: string;
    combined_claimed: string;
  }[];
};
export type SupplierInvoice = {
  id: string;
  number: string;
  supplier: string;
  invoice_number: string;
  invoice_date: string;
  evidence_reference: string;
  po_revision: number;
  total: string;
  currency: "MYR";
  recorded_by: string;
  recorded_at: string;
  status: "awaiting_review" | "needs_clarification" | "reviewed" | "rejected";
  po_snapshot: PurchaseOrder["snapshot"];
  receipt_evidence: Receipt[];
  lines: { line_index: number; quantity: string; unit_price: string }[];
  reviews: {
    actor: string;
    outcome: string;
    reason: string;
    created_at: string;
    checks: InvoiceChecks;
  }[];
};
