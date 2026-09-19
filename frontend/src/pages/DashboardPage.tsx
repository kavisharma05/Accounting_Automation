import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  confirmInvoice,
  downloadLedger,
  fetchDashboard,
  fetchInvoices,
  fetchPendingInvoices,
  markInvoicePaid,
  proposeInvoiceFromDocument,
  rejectInvoice,
  updatePendingAmounts,
  uploadDocument,
  type DashboardSummary,
  type InvoiceRow,
  type PendingInvoice,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatInr(value: string | number) {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(num);
}

function draftTotal(subtotal: string, tax: string) {
  const a = parseFloat(subtotal);
  const b = parseFloat(tax);
  if (Number.isNaN(a) || Number.isNaN(b)) return "";
  return (a + b).toFixed(2);
}

export function DashboardPage() {
  const { session } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [pending, setPending] = useState<PendingInvoice[]>([]);
  const [unpaid, setUnpaid] = useState<InvoiceRow[]>([]);
  const [drafts, setDrafts] = useState<Record<string, { subtotal: string; taxTotal: string }>>({});
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
      const [dash, waiting, invoices] = await Promise.all([
        fetchDashboard(session.orgId, session.token),
        fetchPendingInvoices(session.orgId, session.token),
        fetchInvoices(session.orgId, session.token, "posted"),
      ]);
      setSummary(dash);
      setPending(waiting);
      setUnpaid(
        invoices.filter(
          (inv) => (inv.invoice_type ?? "purchase") === "purchase" && parseFloat(inv.outstanding) > 0,
        ),
      );
      setDrafts((prev) => {
        const next = { ...prev };
        for (const inv of waiting) {
          if (!next[inv.invoice_id]) {
            next[inv.invoice_id] = {
              subtotal: inv.subtotal ?? "",
              taxTotal: inv.tax_total ?? "0",
            };
          }
        }
        return next;
      });
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
        `Check ${proposed.invoice_number} — ${formatInr(proposed.total)}. Fix the numbers if needed, then confirm.`,
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

  async function handleConfirm(inv: PendingInvoice) {
    if (!session || !canWrite) return;
    const draft = drafts[inv.invoice_id] ?? { subtotal: inv.subtotal ?? "0", taxTotal: inv.tax_total ?? "0" };
    setBusy(true);
    setError(null);
    try {
      const updated = await updatePendingAmounts(session.orgId, session.token, inv.invoice_id, {
        subtotal: draft.subtotal || "0",
        tax_total: draft.taxTotal || "0",
      });
      await confirmInvoice(session.orgId, session.token, inv.invoice_id);
      setSuccess(`${inv.invoice_number} is in the books. You owe ${formatInr(updated.total)}.`);
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

  async function handleMarkPaid(inv: InvoiceRow) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    try {
      const paid = await markInvoicePaid(session.orgId, session.token, inv.id);
      setSuccess(`${inv.invoice_number} marked paid — ${formatInr(paid.amount)}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not mark that bill paid");
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
          <p>Send a bill photo. Check the numbers. Confirm. Mark paid when you pay.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void handleExport()}>
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
          <span>Same as WhatsApp. Nothing is booked until you confirm.</span>
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
            {pending.map((inv) => {
              const draft = drafts[inv.invoice_id] ?? {
                subtotal: inv.subtotal ?? "0",
                taxTotal: inv.tax_total ?? "0",
              };
              const total = draftTotal(draft.subtotal, draft.taxTotal);
              return (
                <li key={inv.invoice_id} className="pending-card pending-card-review">
                  <div>
                    <div className="pending-vendor">{inv.party_name || "Vendor"}</div>
                    <div className="pending-meta">
                      {inv.invoice_number}
                      {inv.invoice_date ? ` · ${inv.invoice_date}` : ""}
                      {inv.party_gstin ? ` · GSTIN ${inv.party_gstin}` : ""}
                    </div>
                    <p className="pending-hint">
                      Does this match the paper bill? Change a number if the read was wrong.
                    </p>
                    <div className="pending-amounts">
                      <label>
                        Taxable
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={draft.subtotal}
                          disabled={busy}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [inv.invoice_id]: { ...draft, subtotal: e.target.value },
                            }))
                          }
                        />
                      </label>
                      <label>
                        Tax
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={draft.taxTotal}
                          disabled={busy}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [inv.invoice_id]: { ...draft, taxTotal: e.target.value },
                            }))
                          }
                        />
                      </label>
                      <div className="pending-total-block">
                        <span>Total</span>
                        <strong>{total ? formatInr(total) : "—"}</strong>
                      </div>
                    </div>
                  </div>
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
                        disabled={busy || !total}
                        onClick={() => void handleConfirm(inv)}
                      >
                        Confirm
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="panel inbox-panel">
        <div className="panel-header">Unpaid — mark paid when you pay the vendor</div>
        {unpaid.length === 0 ? (
          <div className="empty-state">No unpaid vendor bills.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Bill</th>
                <th>Still to pay</th>
                {canWrite ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {unpaid.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.party_name || "Vendor"}</td>
                  <td>{inv.invoice_number}</td>
                  <td>{formatInr(inv.outstanding)}</td>
                  {canWrite ? (
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={busy}
                        onClick={() => void handleMarkPaid(inv)}
                      >
                        Mark paid
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {summary ? (
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
      ) : null}

      <p className="home-footnote">
        Month-end GST for the CA? <Link to="/reports">Reports</Link>
      </p>
    </>
  );
}
