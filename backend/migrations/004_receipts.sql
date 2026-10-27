CREATE TABLE receipts (
    id uuid PRIMARY KEY,
    number bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    requisition_id uuid NOT NULL REFERENCES requisitions(id),
    purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id),
    po_revision integer NOT NULL CHECK (po_revision > 0),
    recorded_by text NOT NULL REFERENCES users(id),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    received_on date NOT NULL,
    reference text NOT NULL,
    notes text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('goods','service')),
    lines jsonb NOT NULL,
    po_snapshot jsonb NOT NULL
);
CREATE INDEX receipts_for_pr ON receipts(requisition_id,number);
CREATE TRIGGER immutable_receipt BEFORE UPDATE OR DELETE ON receipts
FOR EACH ROW EXECUTE FUNCTION reject_issued_po_change();
