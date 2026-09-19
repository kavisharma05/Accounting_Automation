import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  confirmInvoice,
  fetchInvoices,
  proposeInvoiceFromDocument,
  searchInvoices,
  uploadDocument,
  type InvoiceRow,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

const STATUSES = ["", "posted", "pending_approval", "draft", "cancelled"];

function formatInr(value: string) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(parseFloat(value));
}

export function InvoicesPage() {
  const { session } = useAuth();
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [status, setStatus] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [pendingProposal, setPendingProposal] = useState<{
    invoice_id: string;
    invoice_number: string;
    total: string;
  } | null>(null);

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const data = searchQ.trim()
        ? await searchInvoices(session.orgId, session.token, searchQ.trim())
        : await fetchInvoices(session.orgId, session.token, status || undefined);
      setInvoices(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }, [session, status, searchQ]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleUpload(file: File | null) {
    if (!session || !canWrite || !file) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    setPendingProposal(null);
    try {
      const uploaded = await uploadDocument(session.orgId, session.token, file);
      const proposed = await proposeInvoiceFromDocument(
        session.orgId,
        session.token,
        uploaded.document_id,
      );
      setPendingProposal({
        invoice_id: proposed.invoice_id,
        invoice_number: proposed.invoice_number,
        total: proposed.total,
      });
      setSuccess(
        `Read as ${proposed.invoice_number} for ${formatInr(proposed.total)} — confirm to book it`,
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload / extraction failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm() {
    if (!session || !canWrite || !pendingProposal) return;
    setBusy(true);
    setError(null);
    try {
      const posted = await confirmInvoice(
        session.orgId,
        session.token,
        pendingProposal.invoice_id,
      );
      setSuccess(`Booked. Journal ${posted.journal_entry_id.slice(0, 8)}…`);
      setPendingProposal(null);
      setShowUpload(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Bills</h1>
          <p>Every bill we have read. Confirm new ones on Home.</p>
        </div>
        {canWrite ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowUpload(!showUpload)}
          >
            {showUpload ? "Cancel" : "Upload bill"}
          </button>
        ) : null}
      </div>

      {success ? <div className="success-banner">{success}</div> : null}

      {showUpload && canWrite ? (
        <div className="panel form-panel">
          <div className="panel-header">Capture a vendor bill</div>
          <div className="form-grid">
            <div className="form-field form-field-wide">
              <label htmlFor="bill-file">Invoice photo or PDF</label>
              <input
                id="bill-file"
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null;
                  e.target.value = "";
                  void handleUpload(file);
                }}
              />
              <span className="field-hint">
                {busy
                  ? "Extracting fields and proposing a journal entry…"
                  : "AI extracts GSTIN, amount, and lines. You confirm before anything posts."}
              </span>
            </div>
            {pendingProposal ? (
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => void handleConfirm()}
                >
                  Confirm & post {pendingProposal.invoice_number}
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search number, party, GSTIN…"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          style={{ minWidth: "220px" }}
        />
        <label htmlFor="status-filter">Status</label>
        <select
          id="status-filter"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          disabled={!!searchQ.trim()}
        >
          <option value="">All</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <p>Loading invoices…</p> : null}

      <div className="panel">
        {!loading && invoices.length === 0 ? (
          <div className="empty-state">No invoices found.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Date</th>
                <th>Type</th>
                <th>Party</th>
                <th>Status</th>
                <th>Total</th>
                <th>Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.invoice_number}</td>
                  <td>{inv.invoice_date}</td>
                  <td>{inv.invoice_type ?? "—"}</td>
                  <td>{inv.party_name ?? "—"}</td>
                  <td>
                    <span className={`badge ${inv.status}`}>{inv.status.replace("_", " ")}</span>
                  </td>
                  <td>{formatInr(inv.total)}</td>
                  <td>{formatInr(inv.outstanding)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
