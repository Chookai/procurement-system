import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Button from "@atlaskit/button/new";
import { setGlobalTheme } from "@atlaskit/tokens/set-global-theme";
import "@atlaskit/css-reset";
import "./style.css";

import type { Auth, PR } from "./types";
import { POReview, POActionBar } from "./POReview";
import { statuses, workflowStatus, nextStep } from "./workflowDisplay";
import {
  ReceivingPanel,
  ReceiptForm,
  ReceiptHistory,
  fulfilmentLabels,
  fulfilmentLabel,
} from "./Receiving";
import { InvoiceForm, InvoicePanel, invoiceLabels } from "./Invoices";
import { PurchaseOrderForm } from "./PurchaseOrderForm";

const roles: Record<string, string> = {
  requester: "Requester",
  approver: "Approver",
  buyer: "Procurement buyer",
  receiver: "Receiver / service acceptor",
  invoice_reviewer: "Invoice reviewer",
};
const currency = (value: string) =>
  new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR" }).format(
    Number(value),
  );

function RequisitionForm({
  record,
  onSave,
  onCancel,
  busy,
  proposal = false,
}: {
  proposal?: boolean;
  record?: PR;
  onSave: (body: object) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
}) {
  const [kind, setKind] = useState(record?.kind || "goods");
  const [count, setCount] = useState(record?.items.length || 1);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const items = Array.from({ length: count }, (_, i) => ({
      description: String(form.get(`description_${i}`)),
      quantity: String(form.get(`quantity_${i}`)),
      unit_price: String(form.get(`price_${i}`)),
    }));
    const body = {
      title: String(form.get("title")),
      kind,
      purpose: String(form.get("purpose")),
      vessel: String(form.get("vessel")),
      location: String(form.get("location")),
      required_date: String(form.get("required_date")),
      supplier_suggestion: String(form.get("supplier_suggestion")),
      items,
    };
    await onSave(
      proposal
        ? {
            ...body,
            supplier: String(form.get("supplier")),
            delivery_terms: String(form.get("delivery_terms")),
            reason: String(form.get("change_reason")),
          }
        : body,
    );
  }
  return (
    <form onSubmit={save} className="request-form">
      <h2>
        {proposal
          ? "Propose PO terms for approval"
          : record
            ? "Edit purchase requisition"
            : "New purchase requisition"}
      </h2>
      <p className="muted">
        {proposal
          ? "Submit the complete replacement terms to Ben. Current issued terms stay active until Chloe issues the approved proposal."
          : "Save a draft first, then submit it to Ben for approval."}
      </p>
      <label>
        Title
        <input
          name="title"
          required
          minLength={3}
          maxLength={150}
          defaultValue={record?.title}
        />
      </label>
      <div className="form-grid">
        <label>
          Purchase type
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as "goods" | "service")}
          >
            <option value="goods">Goods</option>
            <option value="service">Service milestones</option>
          </select>
        </label>
        <label>
          Required date
          <input
            type="date"
            name="required_date"
            required
            defaultValue={record?.required_date}
          />
        </label>
        <label>
          Vessel
          <input
            name="vessel"
            required
            maxLength={120}
            defaultValue={record?.vessel}
          />
        </label>
        <label>
          Location
          <input
            name="location"
            required
            maxLength={120}
            defaultValue={record?.location}
          />
        </label>
      </div>
      <label htmlFor="purpose">Business purpose</label>
      <textarea
        id="purpose"
        name="purpose"
        required
        minLength={5}
        maxLength={2000}
        defaultValue={record?.purpose}
      />
      <label>
        Suggested supplier <span className="muted">(optional)</span>
        <input
          name="supplier_suggestion"
          maxLength={150}
          defaultValue={record?.supplier_suggestion}
        />
      </label>
      {proposal && (
        <>
          <label>
            Confirmed supplier
            <input
              name="supplier"
              required
              minLength={2}
              maxLength={150}
              defaultValue={
                record?.purchase_order?.snapshot.supplier ||
                record?.supplier_suggestion
              }
            />
          </label>
          <label>
            Delivery terms
            <textarea
              name="delivery_terms"
              maxLength={2000}
              defaultValue={record?.purchase_order?.snapshot.delivery_terms}
            />
          </label>
          <label>
            Reason for change
            <textarea
              name="change_reason"
              required
              minLength={1}
              maxLength={1000}
            />
          </label>
        </>
      )}
      <h3>{kind === "goods" ? "Goods requested" : "Service milestones"}</h3>
      {Array.from({ length: count }, (_, i) => (
        <fieldset key={i}>
          <legend>Line {i + 1}</legend>
          <label>
            Description
            <input
              name={`description_${i}`}
              required
              minLength={2}
              maxLength={300}
              defaultValue={record?.items[i]?.description}
            />
          </label>
          <div className="form-grid">
            <label>
              {kind === "goods" ? "Quantity" : "Milestone count"}
              <input
                type="number"
                name={`quantity_${i}`}
                min={kind === "goods" ? ".01" : "1"}
                max="100000"
                step={kind === "goods" ? ".01" : "1"}
                required
                defaultValue={record?.items[i]?.quantity || "1"}
              />
            </label>
            <label>
              {proposal
                ? "Proposed unit price (MYR)"
                : kind === "goods"
                  ? "Unit estimate (MYR)"
                  : "Estimate per milestone (MYR)"}
              <input
                type="number"
                name={`price_${i}`}
                min=".01"
                max="1000000"
                step=".01"
                required
                defaultValue={record?.items[i]?.unit_price}
              />
            </label>
          </div>
        </fieldset>
      ))}
      <div className="actions">
        <Button
          type="button"
          isDisabled={count >= 20 || busy}
          onClick={() => setCount(count + 1)}
        >
          Add line
        </Button>
        {count > 1 && (
          <Button
            type="button"
            isDisabled={busy}
            onClick={() => setCount(count - 1)}
          >
            Remove last line
          </Button>
        )}
      </div>
      <div className="actions form-footer">
        <Button appearance="primary" type="submit" isDisabled={busy}>
          {busy ? "Saving…" : proposal ? "Submit PO proposal" : "Save draft"}
        </Button>
        <Button type="button" onClick={onCancel} isDisabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    new URLSearchParams(location.search).get("theme") === "dark"
      ? "dark"
      : "light",
  );
  const [auth, setAuth] = useState<Auth | null>(null),
    [initializing, setInitializing] = useState(true),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [records, setRecords] = useState<PR[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [form, setForm] = useState<
      "create" | "edit" | "issue" | "proposal" | "receive" | "invoice" | null
    >(null),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all"),
    [receiptFilter, setReceiptFilter] = useState("all"),
    [invoiceFilter, setInvoiceFilter] = useState("all"),
    [reason, setReason] = useState(""),
    [returning, setReturning] = useState(false);
  const keys = useRef(new Map<string, string>());
  const authRef = useRef<Auth | null>(auth);
  authRef.current = auth;
  const record = records.find((row) => row.id === selected);
  useEffect(() => {
    setGlobalTheme({ colorMode: theme });
    document.documentElement.style.colorScheme = theme;
    const url = new URL(location.href);
    url.searchParams.set("theme", theme);
    history.replaceState({}, "", url);
  }, [theme]);
  async function api(
    path: string,
    method = "GET",
    body?: object,
  ): Promise<any> {
    const fingerprint = method + path + JSON.stringify(body);
    let key = keys.current.get(fingerprint);
    if (!key) {
      key = crypto.randomUUID();
      keys.current.set(fingerprint, key);
    }
    const response = await fetch("/api/v1" + path, {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(auth ? { "X-CSRF-Token": auth.csrf_token } : {}),
        "Idempotency-Key": key,
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      if (response.status === 401) {
        setAuth(null);
        setRecords([]);
        setSelected(null);
        setForm(null);
      }
      throw new Error(
        (data?.detail || "Request failed") +
          (data?.fields?.length
            ? " · " +
              data.fields
                .map(
                  (field: any) =>
                    field.loc.slice(1).join(".") + ": " + field.message,
                )
                .join("; ")
            : ""),
      );
    }
    keys.current.delete(fingerprint);
    return data;
  }
  async function refresh() {
    const identity = authRef.current?.user.id;
    setLoading(true);
    try {
      const response = await api("/requisitions");
      if (identity === authRef.current?.user.id) setRecords(response.items);
    } finally {
      if (identity === authRef.current?.user.id) setLoading(false);
    }
  }
  useEffect(() => {
    let cancelled = false;
    fetch("/api/v1/auth/me")
      .then(async (response) => {
        if (response.ok) {
          const result = await response.json();
          if (!cancelled) setAuth(result);
        } else if (response.status !== 401)
          throw new Error("Could not restore your session");
      })
      .catch(() => {
        if (!cancelled)
          setError("Cannot reach the API. Check that the backend is running.");
      })
      .finally(() => {
        if (!cancelled) setInitializing(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (auth) refresh().catch((e) => setError(e.message));
  }, [auth?.user.id]);
  async function perform(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not complete the request",
      );
    } finally {
      setBusy(false);
    }
  }
  async function save(body: object) {
    await perform(async () => {
      const result = await api(
        form === "proposal"
          ? `/requisitions/${record!.id}/po-proposals`
          : record && form === "edit"
            ? `/requisitions/${record.id}`
            : "/requisitions",
        form === "edit" ? "PUT" : "POST",
        form === "edit" || form === "proposal"
          ? { ...body, expected_version: record!.version }
          : body,
      );
      await refresh();
      setSelected(result.id);
      setForm(null);
      setNotice(
        form === "proposal" ? "PO proposal submitted to Ben" : "Draft saved",
      );
    });
  }
  async function invoiceCommand(body: object, review = false) {
    if (!record) return;
    await perform(async () => {
      await api(
        `/requisitions/${record.id}/invoices${review ? "/review" : ""}`,
        "POST",
        { ...body, expected_version: record.version },
      );
      await refresh();
      if (!review) setForm(null);
      setNotice(
        review
          ? "Invoice review outcome recorded"
          : "Supplier invoice captured",
      );
    });
  }
  async function receive(body: object) {
    if (!record) return;
    await perform(async () => {
      await api(`/requisitions/${record.id}/receipts`, "POST", {
        ...body,
        expected_version: record.version,
      });
      await refresh();
      setForm(null);
      setNotice("Receipt / acceptance recorded");
    });
  }
  async function issueOrder(body: object) {
    if (!record) return;
    await perform(async () => {
      const result = await api(
        `/requisitions/${record.id}/purchase-order`,
        "POST",
        { ...body, expected_version: record.version },
      );
      await refresh();
      setForm(null);
      setNotice(`${result.purchase_order.number} issued`);
    });
  }
  async function transition(action: string) {
    if (!record) return;
    await perform(async () => {
      await api(`/requisitions/${record.id}/${action}`, "POST", {
        expected_version: record.version,
        reason: action === "return" ? reason : "",
      });
      await refresh();
      setReason("");
      setReturning(false);
      setNotice(
        action === "approve"
          ? "PR approved"
          : action === "return"
            ? "Returned to the requester"
            : "Submitted to Ben",
      );
    });
  }
  const invoicePanel =
    record && auth ? (
      <InvoicePanel
        key={`invoices-${record.id}`}
        record={record}
        user={auth.user}
        busy={busy}
        onCapture={() => {
          setForm("invoice");
          setError("");
        }}
        onReview={(body) => invoiceCommand(body, true)}
      />
    ) : null;
  const visible = records.filter(
    (row) =>
      (filter === "all" || workflowStatus(row) === filter) &&
      (receiptFilter === "all" || row.fulfilment?.status === receiptFilter) &&
      (invoiceFilter === "all" ||
        row.invoices.some((invoice) => invoice.status === invoiceFilter)) &&
      `${row.number} ${row.title} ${row.vessel}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const editable =
    !!record &&
    auth?.user.id === record.owner_id &&
    auth.user.role === "requester" &&
    ["draft", "returned"].includes(record.status);
  if (initializing)
    return (
      <div className="startup" role="status">
        Connecting to Harbor…
      </div>
    );
  const themeButton = (
    <Button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      {theme === "dark" ? "Light theme" : "Dark theme"}
    </Button>
  );
  if (!auth)
    return (
      <div className="login-page">
        <header>
          <a className="brand" href="/">
            H<span>Harbor</span>
          </a>
          {themeButton}
        </header>
        <main className="login">
          <div className="eyebrow">Demo Marine Logistics</div>
          <h1>Sign in to procurement</h1>
          <p className="muted">Use your assigned PIC account to continue.</p>
          {error && (
            <div className="message error" role="alert">
              {error}
            </div>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              perform(async () => {
                const result = await api("/auth/login", "POST", {
                  username: data.get("username"),
                  password: data.get("password"),
                });
                setRecords([]);
                setSelected(null);
                setForm(null);
                setAuth(result);
              });
            }}
          >
            <label>
              Username
              <input
                name="username"
                autoComplete="username"
                required
                autoFocus
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <Button appearance="primary" type="submit" isDisabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <details>
            <summary>Local demonstration accounts</summary>
            <p>
              Aina · requester
              <br />
              Ben · approver
              <br />
              Chloe · procurement buyer
              <br />
              Dinesh · receiver
              <br />
              Eva · invoice reviewer
            </p>
            <p>
              Usernames are lowercase. Local demo password:{" "}
              <code>harbor-demo</code>.
            </p>
          </details>
          <p className="fine muted">
            Synthetic local workspace · Seeded identity · No registration
          </p>
        </main>
      </div>
    );
  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/">
          H<span>Harbor</span>
        </a>
        <span className="workspace-name">Demo Marine Logistics</span>
        <div className="header-right">
          {themeButton}
          <div className="identity">
            <span className="avatar">{auth.user.name[0]}</span>
            <span>
              <strong>{auth.user.name}</strong>
              <small>{roles[auth.user.role]}</small>
            </span>
          </div>
          <Button
            isDisabled={busy}
            onClick={() =>
              perform(async () => {
                await api("/auth/logout", "POST");
                setAuth(null);
                setRecords([]);
                setSelected(null);
                setForm(null);
                setError("");
                setNotice("");
              })
            }
          >
            Sign out
          </Button>
        </div>
      </header>
      <div className="shell">
        <nav className="sidebar" aria-label="Workspace">
          <div className="eyebrow">Procurement</div>
          <a className="active" href="/">
            Purchase requisitions
          </a>
          <p className="muted">One team. Clear handoffs.</p>
          <div className="scope">
            <strong>First application slice</strong>
            <p>PR approval and PO issuance are connected to the API.</p>
            <p>The AI assistant follows in a later slice.</p>
          </div>
        </nav>
        <main className="workspace">
          <div className="page-heading">
            <div>
              <div className="eyebrow">Workspace / Procurement</div>
              <h1>Purchase requisitions</h1>
              <p className="muted">
                Track requests and keep the next handoff clear.
              </p>
            </div>
            {auth.user.role === "requester" && (
              <Button
                appearance="primary"
                isDisabled={busy}
                onClick={() => {
                  setForm("create");
                  setError("");
                  setNotice("");
                }}
              >
                Create PR
              </Button>
            )}
          </div>
          {error && (
            <div className="message error" role="alert">
              {error}{" "}
              <Button onClick={() => perform(refresh)}>Refresh records</Button>
            </div>
          )}
          {notice && (
            <div className="message success" role="status">
              {notice}
            </div>
          )}
          {form === "invoice" && record ? (
            <InvoiceForm
              record={record}
              busy={busy}
              onSave={(body) => invoiceCommand(body)}
              onCancel={() => setForm(null)}
            />
          ) : form === "receive" && record ? (
            <ReceiptForm
              record={record}
              busy={busy}
              onSave={receive}
              onCancel={() => setForm(null)}
            />
          ) : form === "issue" && record ? (
            <PurchaseOrderForm
              record={record}
              busy={busy}
              onIssue={issueOrder}
              onCancel={() => setForm(null)}
            />
          ) : form ? (
            <RequisitionForm
              key={form + "-" + record?.id + "-" + record?.version}
              proposal={form === "proposal"}
              record={
                form === "proposal" && record
                  ? {
                      ...record,
                      ...(record.purchase_order?.snapshot || {}),
                      items:
                        record.purchase_order?.snapshot.items || record.items,
                    }
                  : form === "edit"
                    ? record
                    : undefined
              }
              busy={busy}
              onSave={save}
              onCancel={() => setForm(null)}
            />
          ) : (
            <>
              <div className="toolbar">
                <input
                  aria-label="Search requisitions"
                  placeholder="Search number, title or vessel"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <select
                  aria-label="Filter by status"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All statuses</option>
                  {Object.entries(statuses).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label} (
                      {
                        records.filter((row) => workflowStatus(row) === value)
                          .length
                      }
                      )
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Filter by fulfilment"
                  value={receiptFilter}
                  onChange={(e) => setReceiptFilter(e.target.value)}
                >
                  <option value="all">All fulfilment</option>
                  {Object.entries(fulfilmentLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Filter by invoice review"
                  value={invoiceFilter}
                  onChange={(e) => setInvoiceFilter(e.target.value)}
                >
                  <option value="all">All invoice reviews</option>
                  {Object.entries(invoiceLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <Button
                  isDisabled={loading || busy}
                  onClick={() => perform(refresh)}
                >
                  {loading ? "Refreshing…" : "Refresh"}
                </Button>
              </div>
              <div className="register-layout">
                <section
                  className="register"
                  aria-label="Purchase requisition register"
                >
                  {loading && records.length === 0 ? (
                    <p role="status" className="empty">
                      Loading requests…
                    </p>
                  ) : visible.length === 0 ? (
                    <div className="empty">
                      <h2>
                        {records.length
                          ? "No matching requests"
                          : "No requests to show"}
                      </h2>
                      <p className="muted">
                        {auth.user.role === "requester"
                          ? "Create a PR draft to start, or change your filters."
                          : "Submitted requests will appear here. Requester drafts are private."}
                      </p>
                    </div>
                  ) : (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Request</th>
                            <th>Status / next action</th>
                            <th>Estimate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {visible.map((row) => (
                            <tr
                              key={row.id}
                              className={selected === row.id ? "selected" : ""}
                            >
                              <td>
                                <button
                                  className="row-link"
                                  onClick={() => {
                                    setSelected(row.id);
                                    setNotice("");
                                    setError("");
                                    setReturning(false);
                                    setReason("");
                                  }}
                                >
                                  <small>{row.number}</small>
                                  {row.title}
                                </button>
                                <small className="muted">{row.vessel}</small>
                              </td>
                              <td>
                                <span
                                  className={`status ${workflowStatus(row)}`}
                                >
                                  {statuses[workflowStatus(row)]}
                                </span>
                                <small className="next-action">
                                  Next: {nextStep(row).action}
                                </small>
                                <small className="muted">
                                  {nextStep(row).owner}
                                </small>
                                {row.fulfilment && (
                                  <>
                                    <span
                                      className={`status fulfilment-${row.fulfilment.status}`}
                                    >
                                      {fulfilmentLabel(row)}
                                    </span>
                                    {[
                                      "po_pending",
                                      "po_approved",
                                      "po_returned",
                                    ].includes(workflowStatus(row)) &&
                                      row.fulfilment.status !== "complete" && (
                                        <small>
                                          Dinesh · Receive against issued
                                          revision {row.fulfilment.po_revision}
                                        </small>
                                      )}
                                  </>
                                )}
                                {row.invoices.length > 0 && (
                                  <div className="invoice-row-status">
                                    <small>
                                      Invoices: {row.invoices.length}
                                    </small>
                                    {Object.entries(invoiceLabels).map(
                                      ([status, label]) =>
                                        row.invoices.some(
                                          (invoice) =>
                                            invoice.status === status,
                                        ) && (
                                          <small key={status}>
                                            {label}:{" "}
                                            {
                                              row.invoices.filter(
                                                (invoice) =>
                                                  invoice.status === status,
                                              ).length
                                            }
                                          </small>
                                        ),
                                    )}
                                    {row.invoices.some((invoice) =>
                                      [
                                        "awaiting_review",
                                        "needs_clarification",
                                      ].includes(invoice.status),
                                    ) && (
                                      <small className="next-action">
                                        Eva · Review invoice
                                      </small>
                                    )}
                                  </div>
                                )}
                              </td>
                              <td className="amount">{currency(row.total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
                <section className="detail" aria-label="Request detail">
                  {!record ? (
                    <div className="empty">
                      <div className="eyebrow">Request detail</div>
                      <h2>Select a requisition</h2>
                      <p className="muted">
                        Inspect its estimate, approval state and activity.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="detail-heading">
                        <div>
                          <div className="eyebrow">
                            {record.number} · Version {record.version}
                          </div>
                          <h2>{record.title}</h2>
                        </div>
                        <span className={`status ${workflowStatus(record)}`}>
                          {statuses[workflowStatus(record)]}
                        </span>
                      </div>
                      {record.status === "approved" && (
                        <POActionBar
                          record={record}
                          user={auth.user}
                          busy={busy}
                          onPropose={() => {
                            setForm("proposal");
                            setError("");
                          }}
                          onPrepare={() => {
                            setForm("issue");
                            setError("");
                          }}
                        />
                      )}
                      {auth.user.role === "invoice_reviewer" && invoicePanel}
                      <ReceivingPanel
                        record={record}
                        user={auth.user}
                        busy={busy}
                        onReceive={() => {
                          setForm("receive");
                          setError("");
                        }}
                      />
                      {auth.user.role !== "invoice_reviewer" && invoicePanel}
                      <div className="total">
                        <span>Estimated value</span>
                        <strong>{currency(record.total)}</strong>
                      </div>
                      <dl>
                        <dt>Purchase type</dt>
                        <dd>
                          {record.kind === "goods"
                            ? "Goods"
                            : "Service milestones"}
                        </dd>
                        <dt>Vessel / location</dt>
                        <dd>
                          {record.vessel} · {record.location}
                        </dd>
                        <dt>Required date</dt>
                        <dd>{record.required_date}</dd>
                        <dt>Suggested supplier</dt>
                        <dd>{record.supplier_suggestion || "No suggestion"}</dd>
                      </dl>
                      <h3>Business purpose</h3>
                      <p>{record.purpose}</p>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>
                                {record.kind === "goods" ? "Item" : "Milestone"}
                              </th>
                              <th>Qty</th>
                              <th>Unit MYR</th>
                            </tr>
                          </thead>
                          <tbody>
                            {record.items.map((line, i) => (
                              <tr key={i}>
                                <td>{line.description}</td>
                                <td>{line.quantity}</td>
                                <td>{line.unit_price}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {editable && (
                        <div className="actions">
                          <Button
                            isDisabled={busy}
                            onClick={() => setForm("edit")}
                          >
                            Edit draft
                          </Button>
                          <Button
                            appearance="primary"
                            isDisabled={busy}
                            onClick={() => transition("submit")}
                          >
                            Submit for approval
                          </Button>
                        </div>
                      )}
                      {record.status === "submitted" &&
                        auth.user.role === "approver" &&
                        record.owner_id !== auth.user.id && (
                          <>
                            <div className="actions">
                              <Button
                                appearance="primary"
                                isDisabled={busy}
                                onClick={() => transition("approve")}
                              >
                                Approve PR
                              </Button>
                              <Button
                                isDisabled={busy}
                                onClick={() => setReturning(!returning)}
                              >
                                Return for changes
                              </Button>
                            </div>
                            {returning && (
                              <form
                                onSubmit={(e) => {
                                  e.preventDefault();
                                  transition("return");
                                }}
                                className="return-form"
                              >
                                <label>
                                  Reason for returning
                                  <textarea
                                    value={reason}
                                    onChange={(e) => setReason(e.target.value)}
                                    minLength={1}
                                    maxLength={1000}
                                    required
                                  />
                                </label>
                                <Button
                                  type="submit"
                                  isDisabled={busy || !reason.trim()}
                                >
                                  Confirm return
                                </Button>
                              </form>
                            )}
                          </>
                        )}
                      {record.purchase_order && (
                        <section
                          className="issued-order"
                          aria-label="Issued purchase order"
                        >
                          <div className="eyebrow">
                            Issued purchase order · revision{" "}
                            {record.purchase_order.revision}
                          </div>
                          <h3>{record.purchase_order.number}</h3>
                          <dl>
                            <dt>Supplier</dt>
                            <dd>{record.purchase_order.snapshot.supplier}</dd>
                            <dt>Issued total</dt>
                            <dd>{currency(record.purchase_order.total)}</dd>
                            <dt>Issued by</dt>
                            <dd>{record.purchase_order.issued_by}</dd>
                            <dt>Issued at</dt>
                            <dd>
                              {new Date(
                                record.purchase_order.issued_at,
                              ).toLocaleString("en-MY")}
                            </dd>
                            <dt>Source PR version</dt>
                            <dd>
                              {record.purchase_order.snapshot.pr_number} · v
                              {record.purchase_order.snapshot
                                .source_pr_version ??
                                record.purchase_order.snapshot
                                  .approved_pr_version}
                            </dd>
                          </dl>
                          <div className="table-scroll">
                            <table>
                              <thead>
                                <tr>
                                  <th>Issued line</th>
                                  <th>Qty</th>
                                  <th>Unit MYR</th>
                                </tr>
                              </thead>
                              <tbody>
                                {record.purchase_order.snapshot.items.map(
                                  (line, i) => (
                                    <tr key={i}>
                                      <td>{line.description}</td>
                                      <td>{line.quantity}</td>
                                      <td>{line.unit_price}</td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </table>
                          </div>
                          <p>
                            <strong>Delivery terms</strong>
                            <br />
                            {record.purchase_order.snapshot.delivery_terms ||
                              "No additional terms recorded"}
                          </p>
                          <p className="muted">
                            Issued terms are preserved as a snapshot. Goods
                            receipt and service acceptance are tracked
                            separately above.
                          </p>
                        </section>
                      )}

                      {record.status === "approved" && (
                        <POReview
                          key={`po-review-${record.id}`}
                          record={record}
                          user={auth.user}
                          busy={busy}
                          onAction={async (action, proposal_id, reason) => {
                            await perform(async () => {
                              await api(
                                `/requisitions/${record.id}/po-proposals/${action}`,
                                "POST",
                                {
                                  expected_version: record.version,
                                  proposal_id,
                                  reason,
                                },
                              );
                              await refresh();
                              setNotice(
                                action === "approve"
                                  ? "PO terms approved; awaiting Chloe’s issuance"
                                  : action === "return"
                                    ? "PO proposal returned"
                                    : "Approved PO terms issued",
                              );
                            });
                          }}
                        />
                      )}
                      <ReceiptHistory record={record} />
                      <h3>Activity</h3>
                      <ol className="activity">
                        {[...record.events].reverse().map((event) => (
                          <li key={event.version}>
                            <strong>{event.actor}</strong> ·{" "}
                            {
                              (
                                {
                                  create: "Created draft",
                                  edit: "Updated draft",
                                  submit: "Submitted for approval",
                                  approve: "Approved PR",
                                  return: "Returned for changes",
                                  issue_po: "Issued purchase order",
                                  receive:
                                    "Recorded receipt / service acceptance",
                                  capture_invoice: "Captured supplier invoice",
                                  review_invoice:
                                    "Recorded invoice review outcome",
                                  propose_po: "Proposed PO terms",
                                  approve_po: "Approved PO proposal",
                                  return_po: "Returned PO proposal",
                                  issue_po_revision: "Issued approved PO terms",
                                } as Record<string, string>
                              )[event.action]
                            }
                            <small>
                              {new Date(event.created_at).toLocaleString(
                                "en-MY",
                              )}{" "}
                              · v{event.version}
                            </small>
                            {event.details.invoice && (
                              <p>
                                {event.details.invoice.invoice_number} ·{" "}
                                {currency(event.details.invoice.total)} ·{" "}
                                {invoiceLabels[event.details.invoice.status]}
                              </p>
                            )}
                            {event.details.purchase_order && (
                              <p>
                                {event.details.purchase_order.number} ·{" "}
                                {currency(event.details.purchase_order.total)}
                              </p>
                            )}
                            {event.details.reason && (
                              <p>{event.details.reason}</p>
                            )}
                          </li>
                        ))}
                      </ol>
                    </>
                  )}
                </section>
              </div>
            </>
          )}
          <aside className="assistant-note">
            <span className="assistant-mark">✧</span>
            <div>
              <strong>Procurement assistant</strong>
              <p className="muted">
                Evidence-backed answers will be added after document ingestion
                and retrieval. You can inspect the saved workflow and activity
                now.
              </p>
            </div>
          </aside>
        </main>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
