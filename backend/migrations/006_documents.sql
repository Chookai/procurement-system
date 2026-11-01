CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE TABLE documents (
 id uuid PRIMARY KEY, title text NOT NULL, owner_id text NOT NULL REFERENCES users(id),
 generation integer NOT NULL DEFAULT 1, active_version uuid, deleted_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE document_versions (
 id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents(id), generation integer NOT NULL,
 filename text NOT NULL, content_hash text NOT NULL, blob_key text NOT NULL UNIQUE,
 pipeline text NOT NULL, state text NOT NULL CHECK(state IN ('uploading','queued','processing','ready','failed','superseded','deleted')),
 error_code text, created_at timestamptz NOT NULL DEFAULT now(), cleaned_at timestamptz,
 UNIQUE(document_id,generation)
);
ALTER TABLE documents ADD FOREIGN KEY(active_version) REFERENCES document_versions(id);
CREATE TABLE document_uploads (
 actor_id text NOT NULL REFERENCES users(id), command_key text NOT NULL, fingerprint text NOT NULL,
 version_id uuid NOT NULL REFERENCES document_versions(id), PRIMARY KEY(actor_id,command_key)
);
CREATE TABLE ingestion_jobs (
 id uuid PRIMARY KEY, version_id uuid NOT NULL UNIQUE REFERENCES document_versions(id),
 state text NOT NULL CHECK(state IN ('queued','running','done','failed','cancelled')),
 attempts integer NOT NULL DEFAULT 0, available_at timestamptz NOT NULL DEFAULT now(),
 lease_until timestamptz, lease_token uuid, error_code text,
 UNIQUE(version_id,id)
);
CREATE INDEX ingestion_pending ON ingestion_jobs(state,available_at);
CREATE TABLE document_passages (
 id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES document_versions(id),
 ordinal integer NOT NULL, line_start integer NOT NULL, line_end integer NOT NULL,
 body text NOT NULL, embedding public.vector(1536) NOT NULL,
 search tsvector GENERATED ALWAYS AS (to_tsvector('english',body)) STORED,
 UNIQUE(version_id,ordinal)
);
CREATE INDEX document_passages_text ON document_passages USING gin(search);
CREATE TABLE document_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents(id),
 version_id uuid REFERENCES document_versions(id), actor_id text REFERENCES users(id),
 action text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
