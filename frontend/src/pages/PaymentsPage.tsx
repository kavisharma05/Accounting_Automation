import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  ApiError,
  createPayment,
  fetchAccounts,
  fetchInvoices,
  fetchParties,
  fetchPayments,
  fetchPilotConfig,
  type InvoiceRow,
  type PaymentRow,
  type PartyRow,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";
const TDS_SECTIONS = ["194C", "194J", "194H", "194I"];

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
  const [parties, setParties] = useState<PartyRow[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [busy, setBusy] = useState(false);

  const [partyId, setPartyId] = useState("");
  const [amount, setAmount] = useState("");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");
  const [applyInvoiceId, setApplyInvoiceId] = useState("");
  const [applyAmount, setApplyAmount] = useState("");

  const [tdsSection, setTdsSection] = useState("194C");

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const [payData, partyData, invData] = await Promise.all([
        fetchPayments(session.orgId, session.token),
        fetchParties(session.orgId, session.token),
        fetchInvoices(session.orgId, session.token, "posted"),
      ]);
      setPayments(payData);
      setParties(partyData);
      setInvoices(invData.filter((i) => parseFloat(i.outstanding) > 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load payments");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!session || !canWrite) return;
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const [config, accounts] = await Promise.all([
        fetchPilotConfig(session.orgId, session.token),
        fetchAccounts(session.orgId, session.token),
      ]);
      const payableId = config.default_payable_account_id;
      const bankCoa = accounts.find((a) => a.code === "1010");
      if (!payableId || !bankCoa) {
        throw new Error("Pilot accounts not configured (payable / bank)");
      }

      const applications =
        applyInvoiceId && applyAmount
          ? [{ invoice_id: applyInvoiceId, amount_applied: applyAmount }]
          : [];

      await createPayment(session.orgId, session.token, {
        party_id: partyId,
        amount,
        payment_date: paymentDate,
        payable_account_id: payableId,
        bank_account_id: bankCoa.id,
        reference: reference || undefined,
        applications,
      });
      setSuccess("Payment recorded successfully");
      setShowForm(false);
      setAmount("");
      setReference("");
      setApplyInvoiceId("");
      setApplyAmount("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create payment");
    } finally {
      setSubmitting(false);
    }
  }

  const partyInvoices = invoices.filter((i) => !partyId || i.party_id === partyId);

  async function handleApplyTds(paymentId: string) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const resp = await fetch(
        `${API_BASE}/organizations/${session.orgId}/payments/${paymentId}/tds`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ section: tdsSection }),
        },
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new ApiError(resp.status, body.detail ?? "TDS failed");
      }
      const data = await resp.json();
      setSuccess(`TDS applied: ₹${data.tds_amount} under ${data.tds_section}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "TDS application failed");
    } finally {
      setBusy(false);
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Payments</h1>
          <p>Record and view vendor payments</p>
        </div>
        {canWrite ? (
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Record payment"}
          </button>
        ) : null}
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}

      {showForm && canWrite ? (
        <div className="panel form-panel">
          <div className="panel-header">New payment</div>
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="form-field">
              <label htmlFor="party">Vendor / party</label>
              <select id="party" value={partyId} onChange={(e) => setPartyId(e.target.value)} required>
                <option value="">Select party</option>
                {parties
                  .filter((p) => p.party_type === "vendor" || p.party_type === "both")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="amount">Amount (₹)</label>
              <input
                id="amount"
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="payment-date">Payment date</label>
              <input
                id="payment-date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="reference">Reference / UTR</label>
              <input
                id="reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="form-field form-field-wide">
              <label htmlFor="apply-invoice">Apply to invoice (optional)</label>
              <div className="inline-fields">
                <select
                  id="apply-invoice"
                  value={applyInvoiceId}
                  onChange={(e) => setApplyInvoiceId(e.target.value)}
                >
                  <option value="">None</option>
                  {partyInvoices.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.invoice_number} — outstanding {formatInr(inv.outstanding)}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="Applied amount"
                  value={applyAmount}
                  onChange={(e) => setApplyAmount(e.target.value)}
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Saving…" : "Save payment"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {loading ? <p>Loading payments…</p> : null}

      {canWrite && payments.length > 0 ? (
        <div className="toolbar">
          <label htmlFor="tds-section">Apply TDS section</label>
          <select id="tds-section" value={tdsSection} onChange={(e) => setTdsSection(e.target.value)}>
            {TDS_SECTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      ) : null}

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
                {canWrite ? <th>TDS</th> : null}
              </tr>
            </thead>
            <tbody>
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td>{payment.payment_date}</td>
                  <td>{formatInr(payment.amount)}</td>
                  <td>{payment.reference ?? "—"}</td>
                  <td>{payment.journal_entry_id ? payment.journal_entry_id.slice(0, 8) + "…" : "—"}</td>
                  {canWrite ? (
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={busy}
                        onClick={() => handleApplyTds(payment.id)}
                      >
                        Apply {tdsSection}
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
