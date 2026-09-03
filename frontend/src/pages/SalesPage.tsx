import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  ApiError,
  createParty,
  createSalesInvoice,
  fetchInvoices,
  fetchParties,
  generateEInvoice,
  postSalesInvoice,
  type InvoiceRow,
  type PartyRow,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatInr(value: string) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(parseFloat(value));
}

export function SalesPage() {
  const { session } = useAuth();
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [customers, setCustomers] = useState<PartyRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [einvoiceResult, setEinvoiceResult] = useState<string | null>(null);

  const [partyId, setPartyId] = useState("");
  const [newCustomerName, setNewCustomerName] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [subtotal, setSubtotal] = useState("");
  const [taxTotal, setTaxTotal] = useState("");

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  const load = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const [inv, parties] = await Promise.all([
        fetchInvoices(session.orgId, session.token, undefined, "sales"),
        fetchParties(session.orgId, session.token),
      ]);
      setInvoices(inv);
      setCustomers(parties.filter((p) => p.party_type === "customer" || p.party_type === "both"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sales data");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAddCustomer(e: FormEvent) {
    e.preventDefault();
    if (!session || !newCustomerName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const party = await createParty(session.orgId, session.token, {
        name: newCustomerName.trim(),
        party_type: "customer",
      });
      setCustomers((prev) => [...prev, party]);
      setPartyId(party.id);
      setNewCustomerName("");
      setSuccess(`Customer "${party.name}" added`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add customer");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateInvoice(e: FormEvent) {
    e.preventDefault();
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await createSalesInvoice(session.orgId, session.token, {
        party_id: partyId,
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate,
        subtotal,
        tax_total: taxTotal || "0",
      });
      setSuccess("Sales invoice created — post it to record in the ledger");
      setShowForm(false);
      setInvoiceNumber("");
      setSubtotal("");
      setTaxTotal("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create invoice");
    } finally {
      setBusy(false);
    }
  }

  async function handlePost(invoiceId: string) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    try {
      await postSalesInvoice(session.orgId, session.token, invoiceId);
      setSuccess("Sales invoice posted");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Post failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleEinvoice(invoiceId: string) {
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    setEinvoiceResult(null);
    try {
      const result = await generateEInvoice(session.orgId, session.token, invoiceId);
      setEinvoiceResult(`IRN: ${result.irn} (Ack: ${result.ack_no})`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "E-invoice failed");
    } finally {
      setBusy(false);
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Sales</h1>
          <p>Create sales invoices, post to ledger, generate e-invoice IRN</p>
        </div>
        {canWrite ? (
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "New sales invoice"}
          </button>
        ) : null}
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}
      {einvoiceResult ? <div className="success-banner">{einvoiceResult}</div> : null}

      {showForm && canWrite ? (
        <div className="panel form-panel">
          <div className="panel-header">New sales invoice</div>
          <form onSubmit={handleCreateInvoice} className="form-grid">
            <div className="form-field">
              <label htmlFor="customer">Customer</label>
              <select id="customer" value={partyId} onChange={(e) => setPartyId(e.target.value)} required>
                <option value="">Select customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="inv-num">Invoice number</label>
              <input
                id="inv-num"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="inv-date">Invoice date</label>
              <input
                id="inv-date"
                type="date"
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="subtotal">Taxable amount (₹)</label>
              <input
                id="subtotal"
                type="number"
                min="0"
                step="0.01"
                value={subtotal}
                onChange={(e) => setSubtotal(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="tax">Tax (₹)</label>
              <input
                id="tax"
                type="number"
                min="0"
                step="0.01"
                value={taxTotal}
                onChange={(e) => setTaxTotal(e.target.value)}
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                Create invoice
              </button>
            </div>
          </form>
          <form onSubmit={handleAddCustomer} className="form-grid" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="form-field form-field-wide">
              <label htmlFor="new-customer">Quick add customer</label>
              <div className="inline-fields">
                <input
                  id="new-customer"
                  placeholder="Customer name"
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.target.value)}
                />
                <button type="submit" className="btn btn-secondary" disabled={busy}>
                  Add customer
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      {loading ? <p>Loading…</p> : null}

      <div className="panel">
        {!loading && invoices.length === 0 ? (
          <div className="empty-state">No sales invoices yet.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Date</th>
                <th>Party</th>
                <th>Status</th>
                <th>Total</th>
                {canWrite ? <th>Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.invoice_number}</td>
                  <td>{inv.invoice_date}</td>
                  <td>{inv.party_name}</td>
                  <td>
                    <span className={`badge ${inv.status}`}>{inv.status.replace("_", " ")}</span>
                  </td>
                  <td>{formatInr(inv.total)}</td>
                  {canWrite ? (
                    <td className="action-cell">
                      {inv.status === "pending_approval" ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={busy}
                          onClick={() => handlePost(inv.id)}
                        >
                          Post
                        </button>
                      ) : null}
                      {inv.status === "posted" ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={busy}
                          onClick={() => handleEinvoice(inv.id)}
                        >
                          E-invoice
                        </button>
                      ) : null}
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
