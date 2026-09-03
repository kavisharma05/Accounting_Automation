import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type ComplianceEntry = {
  id: string;
  title: string;
  entry_type: string;
  due_date: string;
  reference_period: string;
  status: string;
};

type TdsDeduction = {
  id: string;
  payment_id: string;
  tds_section: string;
  tds_amount: string;
};

const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

async function apiGet<T>(path: string, token: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new ApiError(resp.status, "Request failed");
  return resp.json() as Promise<T>;
}

async function apiPost(path: string, token: string, body?: unknown) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, err.detail ?? "Request failed");
  }
  return resp.json();
}

async function apiPatch(path: string, token: string, body: unknown) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new ApiError(resp.status, "Request failed");
  return resp.json();
}

export function CompliancePage() {
  const { session } = useAuth();
  const [entries, setEntries] = useState<ComplianceEntry[]>([]);
  const [deductions, setDeductions] = useState<TdsDeduction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const [cal, tds] = await Promise.all([
        apiGet<ComplianceEntry[]>(
          `/organizations/${session.orgId}/compliance-calendar`,
          session.token,
        ),
        apiGet<TdsDeduction[]>(
          `/organizations/${session.orgId}/tds/deductions`,
          session.token,
        ),
      ]);
      setEntries(cal);
      setDeductions(tds);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGenerate() {
    if (!session || !canWrite) return;
    setError(null);
    try {
      const result = await apiPost(
        `/organizations/${session.orgId}/compliance-calendar/generate`,
        session.token,
      );
      setSuccess(`Generated ${result.created} calendar entries`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generate failed");
    }
  }

  async function handleComplete(id: string) {
    if (!session || !canWrite) return;
    try {
      await apiPatch(
        `/organizations/${session.orgId}/compliance-calendar/${id}`,
        session.token,
        { status: "completed" },
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Compliance</h1>
          <p>TDS deductions and upcoming GST/TDS due dates</p>
        </div>
        {canWrite ? (
          <button type="button" className="btn btn-primary" onClick={handleGenerate}>
            Generate calendar
          </button>
        ) : null}
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}

      <div className="panel" style={{ marginBottom: "1.5rem" }}>
        <div className="panel-header">Upcoming due dates</div>
        {loading ? (
          <div className="empty-state">Loading…</div>
        ) : entries.length === 0 ? (
          <div className="empty-state">No entries — click Generate calendar.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Due date</th>
                <th>Title</th>
                <th>Status</th>
                {canWrite ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.due_date}</td>
                  <td>{e.title}</td>
                  <td>
                    <span className={`badge ${e.status === "completed" ? "posted" : "pending_approval"}`}>
                      {e.status}
                    </span>
                  </td>
                  {canWrite && e.status === "pending" ? (
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleComplete(e.id)}
                      >
                        Mark done
                      </button>
                    </td>
                  ) : canWrite ? (
                    <td />
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">TDS deductions recorded</div>
        {deductions.length === 0 ? (
          <div className="empty-state">No TDS deductions yet — apply from Payments page.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Amount</th>
                <th>Payment</th>
              </tr>
            </thead>
            <tbody>
              {deductions.map((d) => (
                <tr key={d.id}>
                  <td>{d.tds_section}</td>
                  <td>₹{d.tds_amount}</td>
                  <td>{d.payment_id.slice(0, 8)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
