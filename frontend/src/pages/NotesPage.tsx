import { type FormEvent, useEffect, useState } from "react";
import {
  ApiError,
  createCreditNote,
  createDebitNote,
  fetchInvoices,
  postCreditNote,
  postDebitNote,
  type InvoiceRow,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function NotesPage() {
  const { session } = useAuth();
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [noteType, setNoteType] = useState<"credit" | "debit">("credit");
  const [invoiceId, setInvoiceId] = useState("");
  const [noteNumber, setNoteNumber] = useState("");
  const [noteDate, setNoteDate] = useState(new Date().toISOString().slice(0, 10));
  const [subtotal, setSubtotal] = useState("");
  const [taxTotal, setTaxTotal] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchInvoices(session.orgId, session.token, "posted");
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
  }, [session]);

  const selected = invoices.find((i) => i.id === invoiceId);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    const payload = {
      original_invoice_id: invoiceId,
      note_number: noteNumber,
      note_date: noteDate,
      subtotal,
      tax_total: taxTotal || "0",
      reason: reason || undefined,
    };
    try {
      if (noteType === "credit") {
        const note = await createCreditNote(session.orgId, session.token, payload);
        await postCreditNote(session.orgId, session.token, note.id);
        setSuccess(`Credit note ${note.note_number} posted`);
      } else {
        const note = await createDebitNote(session.orgId, session.token, payload);
        await postDebitNote(session.orgId, session.token, note.id);
        setSuccess(`Debit note ${note.note_number} posted`);
      }
      setNoteNumber("");
      setSubtotal("");
      setTaxTotal("");
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to post note");
    } finally {
      setBusy(false);
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Credit / debit notes</h1>
          <p>Issue notes against posted invoices — credit reduces outstanding</p>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}

      {canWrite ? (
        <div className="panel form-panel">
          <div className="panel-header">New note</div>
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="form-field">
              <label htmlFor="note-type">Type</label>
              <select
                id="note-type"
                value={noteType}
                onChange={(e) => setNoteType(e.target.value as "credit" | "debit")}
              >
                <option value="credit">Credit note</option>
                <option value="debit">Debit note</option>
              </select>
            </div>
            <div className="form-field form-field-wide">
              <label htmlFor="orig-invoice">Original invoice</label>
              <select
                id="orig-invoice"
                value={invoiceId}
                onChange={(e) => setInvoiceId(e.target.value)}
                required
              >
                <option value="">Select posted invoice</option>
                {invoices.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_type} {inv.invoice_number} — {inv.party_name} (outstanding ₹
                    {inv.outstanding})
                  </option>
                ))}
              </select>
            </div>
            {selected && noteType === "credit" ? (
              <div className="field-hint form-field-wide">
                Max credit for this invoice: outstanding ₹{selected.outstanding}
              </div>
            ) : null}
            <div className="form-field">
              <label htmlFor="note-num">Note number</label>
              <input
                id="note-num"
                value={noteNumber}
                onChange={(e) => setNoteNumber(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="note-date">Note date</label>
              <input
                id="note-date"
                type="date"
                value={noteDate}
                onChange={(e) => setNoteDate(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="note-subtotal">Taxable amount (₹)</label>
              <input
                id="note-subtotal"
                type="number"
                min="0.01"
                step="0.01"
                value={subtotal}
                onChange={(e) => setSubtotal(e.target.value)}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="note-tax">Tax (₹)</label>
              <input
                id="note-tax"
                type="number"
                min="0"
                step="0.01"
                value={taxTotal}
                onChange={(e) => setTaxTotal(e.target.value)}
              />
            </div>
            <div className="form-field form-field-wide">
              <label htmlFor="reason">Reason</label>
              <input
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy || loading}>
                Create & post note
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-state">Viewer role — notes are read-only via ledger reports.</div>
      )}
    </>
  );
}
