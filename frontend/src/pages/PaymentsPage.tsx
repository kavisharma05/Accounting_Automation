import { useEffect, useState } from "react";
import { ApiError, fetchPayments, type PaymentRow } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatInr(value: string) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(parseFloat(value));
}

export function PaymentsPage() {
  const { session } = useAuth();
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPayments(session.orgId, session.token);
        if (!cancelled) setPayments(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load payments");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session]);

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Payments</h1>
          <p>Recorded payments against vendor invoices</p>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <p>Loading payments…</p> : null}

      <div className="panel">
        {!loading && payments.length === 0 ? (
          <div className="empty-state">No payments recorded yet.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Reference</th>
                <th>Journal entry</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td>{payment.payment_date}</td>
                  <td>{formatInr(payment.amount)}</td>
                  <td>{payment.reference ?? "—"}</td>
                  <td>{payment.journal_entry_id ? payment.journal_entry_id.slice(0, 8) + "…" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
