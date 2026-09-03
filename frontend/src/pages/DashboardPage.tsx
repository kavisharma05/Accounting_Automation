import { useEffect, useState } from "react";
import { ApiError, downloadLedger, fetchDashboard, type DashboardSummary } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatCard } from "../components/StatCard";

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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchDashboard(session.orgId, session.token);
        if (!cancelled) setSummary(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session]);

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
          <h1>Overview</h1>
          <p>Financial snapshot for {session.orgName}</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={handleExport}>
          Export ledger (Excel)
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <p>Loading dashboard…</p> : null}

      {summary ? (
        <>
          <div className="card-grid">
            <StatCard label="Pending approvals" value={summary.pending_approvals} />
            <StatCard label="Outstanding invoices" value={summary.outstanding_invoices_count} />
            <StatCard label="Outstanding total" value={formatInr(summary.outstanding_total)} />
            <StatCard label="Recent entries" value={summary.recent_journal_entries.length} />
          </div>

          <div className="panel">
            <div className="panel-header">Recent journal entries</div>
            {summary.recent_journal_entries.length === 0 ? (
              <div className="empty-state">No posted journal entries yet.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Entry #</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.recent_journal_entries.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.entry_date}</td>
                      <td>{entry.entry_number}</td>
                      <td>{entry.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : null}
    </>
  );
}
