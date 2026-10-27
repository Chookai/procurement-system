CREATE TABLE invoices (
    id uuid PRIMARY KEY,
    number bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    requisition_id uuid NOT NULL REFERENCES requisitions(id),
    purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id),
    po_revision integer NOT NULL CHECK (po_revision > 0),
    recorded_by text NOT NULL REFERENCES users(id),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    supplier text NOT NULL,
    supplier_key text NOT NULL,
    invoice_number text NOT NULL,
    number_key text NOT NULL,
    invoice_date date NOT NULL,
    evidence_reference text NOT NULL,
    lines jsonb NOT NULL,
    total_myr numeric(20,2) NOT NULL CHECK (total_myr > 0),
    po_snapshot jsonb NOT NULL,
    receipt_evidence jsonb NOT NULL,
    UNIQUE (supplier_key,number_key)
);
CREATE INDEX invoices_for_pr ON invoices(requisition_id,number);
CREATE TABLE invoice_reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id uuid NOT NULL REFERENCES invoices(id),
    actor_id text NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    outcome text NOT NULL CHECK (outcome IN ('reviewed','needs_clarification','rejected')),
    reason text NOT NULL CHECK (length(btrim(reason)) > 0),
    checks jsonb NOT NULL
);
CREATE INDEX reviews_for_invoice ON invoice_reviews(invoice_id,id);
CREATE TRIGGER immutable_invoice BEFORE UPDATE OR DELETE ON invoices
FOR EACH ROW EXECUTE FUNCTION reject_issued_po_change();
CREATE TRIGGER immutable_invoice_review BEFORE UPDATE OR DELETE ON invoice_reviews
FOR EACH ROW EXECUTE FUNCTION reject_issued_po_change();
