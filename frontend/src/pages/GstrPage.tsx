import { useState } from "react";
import { ApiError, downloadGstr1, fetchGstr3b, type Gstr3bSummary } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatInr(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function monthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export function GstrPage() {
  const { session } = useAuth();
  const bounds = monthBounds();
  const [periodStart, setPeriodStart] = useState(bounds.start);
  const [periodEnd, setPeriodEnd] = useState(bounds.end);
  const [summary, setSummary] = useState<Gstr3bSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadSummary() {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGstr3b(session.orgId, session.token, periodStart, periodEnd);
      setSummary(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load GSTR summary");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    if (!session) return;
    setError(null);
    try {
      const blob = await downloadGstr1(session.orgId, session.token, periodStart, periodEnd);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gstr1-${periodStart}-${periodEnd}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed");
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>GSTR worksheets</h1>
          <p>Preparation only — verify with your CA before filing</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={handleExport}>
          Download Excel
        </button>
      </div>

      <div className="toolbar">
        <label htmlFor="period-start">From</label>
        <input
          id="period-start"
          type="date"
          value={periodStart}
          onChange={(e) => setPeriodStart(e.target.value)}
        />
        <label htmlFor="period-end">To</label>
        <input
          id="period-end"
          type="date"
          value={periodEnd}
          onChange={(e) => setPeriodEnd(e.target.value)}
        />
        <button type="button" className="btn btn-primary" onClick={loadSummary} disabled={loading}>
          {loading ? "Loading…" : "Load summary"}
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {summary ? (
        <>
          <div className="card-grid">
            <div className="stat-card">
              <div className="label">Outward taxable supplies</div>
              <div className="value">{formatInr(summary.outward_taxable_supplies)}</div>
            </div>
            <div className="stat-card">
              <div className="label">Output tax</div>
              <div className="value">{formatInr(summary.output_tax)}</div>
            </div>
            <div className="stat-card">
              <div className="label">Input tax credit</div>
              <div className="value">{formatInr(summary.input_tax_credit)}</div>
            </div>
            <div className="stat-card">
              <div className="label">Net tax payable</div>
              <div className="value">{formatInr(summary.net_tax_payable)}</div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-header">Period detail</div>
            <table className="data-table">
              <tbody>
                <tr>
                  <td>Sales invoices</td>
                  <td>{summary.sales_invoice_count}</td>
                </tr>
                <tr>
                  <td>Purchase invoices</td>
                  <td>{summary.purchase_invoice_count}</td>
                </tr>
                <tr>
                  <td>Period</td>
                  <td>
                    {summary.period_start} → {summary.period_end}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="empty-state">Select a period and load the GSTR-3B summary.</div>
      )}
    </>
  );
}
