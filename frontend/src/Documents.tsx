import React, { useEffect, useRef, useState } from "react";
import Button from "@atlaskit/button/new";
import type { Auth } from "./types";

type Version = {
  id: string;
  generation: number;
  filename: string;
  state: string;
  error_code: string | null;
  attempts: number | null;
  pipeline: string;
  content_hash: string;
};
type Document = {
  id: string;
  title: string;
  generation: number;
  active_version: string | null;
  versions: Version[];
};
type Passage = {
  id: string;
  title: string;
  generation: number;
  line_start: number;
  line_end: number;
  body: string;
  source_url: string;
};
type Api = (path: string, method?: string, body?: object) => Promise<any>;
const labels: Record<string, string> = {
  uploading: "Source upload incomplete",
  queued: "Waiting for worker",
  processing: "Processing",
  ready: "Searchable",
  failed: "Failed — action needed",
  superseded: "Previous version",
  deleted: "Deleted",
};

export function Documents({ auth, api }: { auth: Auth; api: Api }) {
  const [items, setItems] = useState<Document[]>([]);
  const [selected, setSelected] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Passage[]>([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const keys = useRef(new Map<string, { key: string; generation: number | undefined }>());
  const buyer = auth.user.role === "buyer";
  const replacement = items.find((d) => d.id === selected);
  async function refresh() {
    setItems((await api("/documents")).items);
  }
  useEffect(() => {
    let alive = true;
    const load = () =>
      api("/documents")
        .then((d) => {
          if (alive) setItems(d.items);
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    load();
    const timer = setInterval(load, 4000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [auth.user.id]);
  async function perform(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const form = event.currentTarget;
    await perform(async () => {
      if (file.size > 65536 || !/\.(txt|md)$/i.test(file.name))
        throw Error("Choose a UTF-8 .md or .txt file, up to 64 KiB.");
      const bytes = await file.arrayBuffer();
      const hash = Array.from(
        new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
      )
        .map((x) => x.toString(16).padStart(2, "0"))
        .join("");
      const fingerprint = JSON.stringify([
        selected,
        title,
        file.name,
        hash,
      ]);
      let pending = keys.current.get(fingerprint);
      if (!pending) {
        pending = { key: crypto.randomUUID(), generation: replacement?.generation };
        keys.current.set(fingerprint, pending);
      }
      const params = new URLSearchParams({ filename: file.name, title });
      if (replacement)
        params.set("expected_generation", String(pending.generation));
      const response = await fetch(
        "/api/v1/documents" +
          (replacement ? `/${replacement.id}/versions` : "") +
          "?" +
          params,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/octet-stream",
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": pending.key,
          },
          body: bytes,
        },
      );
      const body = await response.json();
      if (!response.ok) {
        // A conflict ends this attempt; a later submission uses refreshed terms.
        if (response.status === 409) keys.current.delete(fingerprint);
        throw Error(
          typeof body.detail === "string"
            ? body.detail
            : "Upload failed. Refresh and try again.",
        );
      }
      keys.current.delete(fingerprint);
      setFile(null);
      setTitle("");
      setSelected("");
      form.reset();
      setResults([]);
      setSearched(false);
      setNotice(
        "Source stored. Waiting for ingestion; the worker must be running.",
      );
      await refresh();
    });
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Workspace / Evidence</div>
          <h1>Policy documents</h1>
          <p className="muted">
            Shared team policies with traceable versions and passages.
          </p>
        </div>
        <Button isDisabled={busy} onClick={() => perform(refresh)}>
          Refresh documents
        </Button>
      </div>
      {error && (
        <div className="message error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="message success" role="status">
          {notice}
        </div>
      )}
      <div className="document-callout">
        Chloe manages the shared policy library. All five team members can read
        published evidence. Supplier attachments and confidential PR documents
        are outside this library.
      </div>
      {buyer && (
        <form className="request-form document-upload" onSubmit={upload}>
          <h2>
            {replacement ? "Replace policy source" : "Upload a team policy"}
          </h2>
          <p className="muted">
            UTF-8 Markdown or text · maximum 64 KiB. A replacement keeps the
            current searchable version until processing succeeds.
          </p>
          <label>
            Policy to update
            <select
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setTitle(
                  items.find((d) => d.id === e.target.value)?.title || "",
                );
              }}
            >
              <option value="">New document</option>
              {items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Document title
            <input
              required
              minLength={3}
              maxLength={150}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Source file
            <input
              type="file"
              accept=".md,.txt,text/plain,text/markdown"
              required
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
          <Button appearance="primary" type="submit" isDisabled={busy || !file}>
            {replacement ? "Upload replacement" : "Upload document"}
          </Button>
        </form>
      )}
      <section className="document-search">
        <h2>Find supporting passages</h2>
        <p className="muted">
          Searches only complete, current versions using full-text and semantic
          retrieval. This returns evidence, not an AI-generated answer.
        </p>
        <form
          className="document-search-form"
          onSubmit={(e) => {
            e.preventDefault();
            perform(async () => {
              setResults([]);
              setSearched(false);
              const r = await api(
                "/documents/search?q=" + encodeURIComponent(query),
              );
              setResults(r.items);
              setSearched(true);
            });
          }}
        >
          <label>
            Search policies
            <input
              required
              minLength={2}
              maxLength={500}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <Button appearance="primary" type="submit" isDisabled={busy}>
            Search evidence
          </Button>
        </form>
        {searched && results.length === 0 && (
          <p role="status">No published passages found.</p>
        )}
        <div aria-live="polite">
          {results.map((p) => (
            <article className="document-card" key={p.id}>
              <h3>
                {p.title} · Version {p.generation}
              </h3>
              <p className="fine">
                Lines {p.line_start}–{p.line_end} · Passage {p.id}
              </p>
              <pre className="document-passage">{p.body}</pre>
              <a href={p.source_url}>Download cited source</a>
            </article>
          ))}
        </div>
      </section>
      <h2>
        Library <span className="muted">({items.length})</span>
      </h2>
      {!items.length && (
        <p>
          No policies yet. Ask Chloe to upload a synthetic .md or .txt policy.
        </p>
      )}
      {items.map((d) => (
        <article className="document-card" key={d.id}>
          <h3>{d.title}</h3>
          <p>
            <strong>
              {d.versions[0].error_code === "upload_expired"
                ? "Source upload expired"
                : labels[d.versions[0].state] || d.versions[0].state}
            </strong>{" "}
            · Latest source: version {d.generation}
          </p>
          <p className="muted">
            {d.active_version
              ? `Search uses version ${d.versions.find((v) => v.id === d.active_version)?.generation}.`
              : "No version is searchable yet."}
          </p>
          {d.versions[0].error_code === "upload_expired" ? (
            <p role="status">
              The incomplete upload expired. Chloe can upload a replacement
              source.
            </p>
          ) : (
            d.versions[0].error_code && (
              <p role="status">
                Processing failed.{" "}
                {d.versions[0].state === "failed"
                  ? "Chloe can retry the latest source."
                  : "The worker will retry within the attempt limit."}{" "}
                Attempts: {d.versions[0].attempts ?? 0}/3.
              </p>
            )
          )}
          {buyer && (
            <div className="document-actions">
              <Button
                isDisabled={busy}
                onClick={() => {
                  setSelected(d.id);
                  setTitle(d.title);
                  document
                    .querySelector(".document-upload")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                Replace source
              </Button>
              {d.versions[0].state === "failed" && (
                <Button
                  appearance="primary"
                  isDisabled={busy}
                  onClick={() =>
                    perform(async () => {
                      await api(`/documents/${d.id}/retry`, "POST");
                      setNotice("Retry queued.");
                      await refresh();
                    })
                  }
                >
                  Retry ingestion
                </Button>
              )}
              <Button
                appearance="danger"
                isDisabled={busy}
                onClick={() => setDeleting(d.id)}
              >
                Delete policy
              </Button>
            </div>
          )}
          {deleting === d.id && (
            <div className="document-callout">
              <p>
                Delete this policy and remove all its passages from search?
                Stored sources will be cleaned up by the worker.
              </p>
              <Button
                appearance="danger"
                isDisabled={busy}
                onClick={() =>
                  perform(async () => {
                    await api(
                      `/documents/${d.id}?expected_generation=${d.generation}`,
                      "DELETE",
                    );
                    setDeleting(null);
                    setResults([]);
                    setSearched(false);
                    setSelected("");
                    setNotice("Policy removed from search.");
                    await refresh();
                  })
                }
              >
                Confirm deletion
              </Button>{" "}
              <Button onClick={() => setDeleting(null)}>Cancel</Button>
            </div>
          )}
          <details>
            <summary>Source versions and processing details</summary>
            {d.versions.map((v) => (
              <section className="document-version" key={v.id}>
                <strong>
                  Version {v.generation} · {labels[v.state]}
                </strong>
                <p>
                  {v.filename} · Source {v.id}
                </p>
                <p className="fine">
                  SHA-256: {v.content_hash}
                  <br />
                  Pipeline: {v.pipeline}
                </p>
                {!["uploading", "deleted"].includes(v.state) && (
                  <a href={`/api/v1/documents/${d.id}/versions/${v.id}/source`}>
                    Download original text
                  </a>
                )}
              </section>
            ))}
          </details>
        </article>
      ))}
    </>
  );
}
