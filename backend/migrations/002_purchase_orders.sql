CREATE TABLE purchase_orders (
    id uuid PRIMARY KEY,
    number bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    requisition_id uuid NOT NULL UNIQUE REFERENCES requisitions(id),
    issued_by text NOT NULL REFERENCES users(id),
    issued_at timestamptz NOT NULL DEFAULT now(),
    snapshot jsonb NOT NULL,
    total_myr numeric(20,2) NOT NULL CHECK (total_myr > 0)
);
CREATE FUNCTION reject_issued_po_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Issued purchase orders are immutable; preserve history with a new revision';
END;
$$;
CREATE TRIGGER immutable_purchase_order BEFORE UPDATE OR DELETE ON purchase_orders
FOR EACH ROW EXECUTE FUNCTION reject_issued_po_change();
