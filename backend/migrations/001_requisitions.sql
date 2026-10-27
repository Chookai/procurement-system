CREATE TABLE users (
    id text PRIMARY KEY,
    name text NOT NULL,
    role text NOT NULL CHECK (role IN ('requester','approver','buyer','receiver','invoice_reviewer')),
    password_hash text NOT NULL,
    active boolean NOT NULL DEFAULT true
);
CREATE TABLE sessions (
    id uuid PRIMARY KEY,
    user_id text NOT NULL REFERENCES users(id),
    expires_at timestamptz NOT NULL,
    revoked boolean NOT NULL DEFAULT false
);
CREATE TABLE requisitions (
    id uuid PRIMARY KEY,
    number bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    owner_id text NOT NULL REFERENCES users(id),
    status text NOT NULL CHECK (status IN ('draft','submitted','returned','approved')),
    version integer NOT NULL DEFAULT 1,
    data jsonb NOT NULL,
    total_myr numeric(20,2) NOT NULL CHECK (total_myr > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX requisitions_owner ON requisitions(owner_id);
CREATE TABLE audit_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    requisition_id uuid NOT NULL REFERENCES requisitions(id),
    actor_id text NOT NULL REFERENCES users(id),
    action text NOT NULL,
    version integer NOT NULL,
    details jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_requisition ON audit_events(requisition_id, id);
CREATE TABLE commands (
    actor_id text NOT NULL REFERENCES users(id),
    key text NOT NULL,
    fingerprint text NOT NULL,
    response jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_id, key)
);
