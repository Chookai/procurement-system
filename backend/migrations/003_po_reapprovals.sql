CREATE TABLE po_proposals (
    id uuid PRIMARY KEY,
    requisition_id uuid NOT NULL REFERENCES requisitions(id),
    base_revision integer NOT NULL CHECK (base_revision >= 0),
    proposed_by text NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    snapshot jsonb NOT NULL,
    total_myr numeric(20,2) NOT NULL CHECK (total_myr > 0),
    reason text NOT NULL,
    status text NOT NULL CHECK (status IN ('pending','approved','returned','issued')),
    decided_by text REFERENCES users(id),
    decided_at timestamptz,
    decision_reason text NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX one_open_po_proposal ON po_proposals(requisition_id)
WHERE status IN ('pending','approved');
CREATE TABLE po_revisions (
    id uuid PRIMARY KEY,
    purchase_order_id uuid NOT NULL REFERENCES purchase_orders(id),
    revision integer NOT NULL CHECK (revision >= 2),
    proposal_id uuid NOT NULL UNIQUE REFERENCES po_proposals(id),
    issued_by text NOT NULL REFERENCES users(id),
    issued_at timestamptz NOT NULL DEFAULT now(),
    snapshot jsonb NOT NULL,
    total_myr numeric(20,2) NOT NULL CHECK (total_myr > 0),
    UNIQUE (purchase_order_id,revision)
);
CREATE TRIGGER immutable_po_revision BEFORE UPDATE OR DELETE ON po_revisions
FOR EACH ROW EXECUTE FUNCTION reject_issued_po_change();
CREATE FUNCTION protect_po_proposal_terms() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'PO proposals preserve review history'; END IF;
    IF (NEW.id,NEW.requisition_id,NEW.base_revision,NEW.proposed_by,NEW.created_at,NEW.snapshot,NEW.total_myr,NEW.reason)
        IS DISTINCT FROM (OLD.id,OLD.requisition_id,OLD.base_revision,OLD.proposed_by,OLD.created_at,OLD.snapshot,OLD.total_myr,OLD.reason)
    THEN RAISE EXCEPTION 'Proposed terms are immutable; submit a new proposal'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER immutable_po_proposal_terms BEFORE UPDATE OR DELETE ON po_proposals
FOR EACH ROW EXECUTE FUNCTION protect_po_proposal_terms();
