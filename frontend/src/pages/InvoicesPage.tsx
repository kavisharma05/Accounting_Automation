import { useEffect, useState } from "react";
import { ApiError, fetchInvoices, searchInvoices, type InvoiceRow } from "../api/client";
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = searchQ.trim()
          ? await searchInvoices(session.orgId, session.token, searchQ.trim())
          : await fetchInvoices(session.orgId, session.token, status || undefined);
        if (!cancelled) setInvoices(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load invoices");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session, status, searchQ]);

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Invoices</h1>
          <p>Purchase and sales invoices with outstanding balances</p>
        </div>
      </div>

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
