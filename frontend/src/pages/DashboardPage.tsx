import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  confirmInvoice,
  downloadLedger,
  rejectInvoice,
  fetchDashboard,
  fetchPendingInvoices,
  proposeInvoiceFromDocument,
  uploadDocument,
  type DashboardSummary,
  type PendingInvoice,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatInr(value: string | number) {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

export function DashboardPage() {
  const { session } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [pending, setPending] = useState<PendingInvoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const [dash, waiting] = await Promise.all([
        fetchDashboard(session.orgId, session.token),
        fetchPendingInvoices(session.orgId, session.token),
      ]);
      setSummary(dash);
      setPending(waiting);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load home");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleUpload(file: File | null) {
    if (!session || !canWrite || !file) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const uploaded = await uploadDocument(session.orgId, session.token, file);
      const proposed = await proposeInvoiceFromDocument(
        session.orgId,
        session.token,
        uploaded.document_id,
      );
      setSuccess(
        `This is ${proposed.invoice_number} — ${formatInr(proposed.total)}. Confirm below to book it.`,
      );
      await load();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not read that bill";
      if (message.toLowerCase().includes("duplicate")) {
        setError("This bill is already here. Confirm it below, or dismiss it and drop the photo again.");
        await load();
      } else {
        setError(message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm(invoiceId: string, invoiceNumber: string, total: string) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    try {
      await confirmInvoice(session.orgId, session.token, invoiceId);
      setSuccess(`${invoiceNumber} is in the books. You owe ${formatInr(total)}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not post that bill");
    } finally {
      setBusy(false);
    }
  }

  async function handleDismiss(invoiceId: string, invoiceNumber: string) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    try {
      await rejectInvoice(session.orgId, session.token, invoiceId);
      setSuccess(`${invoiceNumber} dismissed. Drop the bill again if you want a fresh read.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not dismiss that bill");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!session) return;
    const blob = await downloadLedger(session.orgId, session.token);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ledger.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Home</h1>
          <p>Send a bill photo. Confirm the numbers. The books update.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={handleExport}>
          Send ledger to CA
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}

      {canWrite ? (
        <label
          className={`dropzone${dragOver ? " dropzone-active" : ""}${busy ? " dropzone-busy" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            void handleUpload(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              e.target.value = "";
              void handleUpload(file);
            }}
          />
          <strong>{busy ? "Reading the bill…" : "Drop a bill photo here, or click to upload"}</strong>
          <span>Same as sending it on WhatsApp. Nothing is booked until you confirm.</span>
        </label>
      ) : null}

      <div className="panel inbox-panel">
        <div className="panel-header">Waiting for your yes</div>
        {loading && pending.length === 0 ? (
          <div className="empty-state">Loading…</div>
        ) : pending.length === 0 ? (
          <div className="empty-state">No bills waiting. Upload one above.</div>
        ) : (
          <ul className="pending-list">
            {pending.map((inv) => (
              <li key={inv.invoice_id} className="pending-card">
                <div>
                  <div className="pending-vendor">{inv.party_name || "Vendor"}</div>
                  <div className="pending-meta">
                    {inv.invoice_number}
                    {inv.invoice_date ? ` · ${inv.invoice_date}` : ""}
                  </div>
                </div>
                <div className="pending-total">{formatInr(inv.total)}</div>
                {canWrite ? (
                  <div className="pending-actions">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => void handleDismiss(inv.invoice_id, inv.invoice_number)}
                    >
                      Dismiss
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busy}
                      onClick={() => void handleConfirm(inv.invoice_id, inv.invoice_number, inv.total)}
                    >
                      Confirm
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      {summary ? (
        <>
          <div className="card-grid">
            <div className="stat-card">
              <div className="label">Unpaid bills</div>
              <div className="value">{summary.outstanding_invoices_count}</div>
            </div>
            <div className="stat-card">
              <div className="label">Still to pay</div>
              <div className="value">{formatInr(summary.outstanding_total)}</div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">Just booked</div>
            {summary.recent_journal_entries.length === 0 ? (
              <div className="empty-state">Nothing in the books yet.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>What happened</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.recent_journal_entries.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.entry_date}</td>
                      <td>{entry.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : null}

      <p className="home-footnote">
        Paid a vendor? <Link to="/payments">Mark it paid</Link>
        {" · "}
        Month-end GST for the CA? <Link to="/reports">Reports</Link>
      </p>
    </>
  );
}
