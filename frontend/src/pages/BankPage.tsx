import { type FormEvent, useEffect, useState } from "react";
import {
  ApiError,
  createBankAccount,
  fetchAccounts,
  fetchBankAccounts,
  importBankCsv,
  reconcileBank,
  type BankAccountRow,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function BankPage() {
  const { session } = useAuth();
  const [banks, setBanks] = useState<BankAccountRow[]>([]);
  const [selectedBank, setSelectedBank] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [newBankName, setNewBankName] = useState("Primary Bank");

  const canWrite =
    session?.role === "owner" || session?.role === "accountant" || session?.role === "admin";

  async function load() {
    if (!session) return;
    setLoading(true);
    try {
      const data = await fetchBankAccounts(session.orgId, session.token);
      setBanks(data);
      if (data.length && !selectedBank) {
        setSelectedBank(data[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bank accounts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  async function handleCreateBank(e: FormEvent) {
    e.preventDefault();
    if (!session || !canWrite) return;
    setBusy(true);
    setError(null);
    try {
      const accounts = await fetchAccounts(session.orgId, session.token);
      const bankCoa = accounts.find((a) => a.code === "1010");
      if (!bankCoa) throw new Error("Bank account (1010) not found in chart of accounts");
      await createBankAccount(session.orgId, session.token, {
        name: newBankName,
        chart_of_account_id: bankCoa.id,
      });
      setSuccess("Bank account registered");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create bank account");
    } finally {
      setBusy(false);
    }
  }

  async function handleImport(file: File | null) {
    if (!session || !canWrite || !selectedBank || !file) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await importBankCsv(session.orgId, session.token, selectedBank, file);
      setSuccess(`Imported ${result.imported} transactions`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReconcile() {
    if (!session || !canWrite || !selectedBank) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await reconcileBank(session.orgId, session.token, selectedBank);
      setSuccess(`Auto-matched ${result.matches} transactions`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reconciliation failed");
    } finally {
      setBusy(false);
    }
  }

  if (!session) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Bank</h1>
          <p>Import statements and reconcile against payments</p>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? <div className="success-banner">{success}</div> : null}

      {canWrite && banks.length === 0 && !loading ? (
        <div className="panel form-panel">
          <div className="panel-header">Register bank account</div>
          <form onSubmit={handleCreateBank} className="form-grid">
            <div className="form-field">
              <label htmlFor="bank-name">Display name</label>
              <input
                id="bank-name"
                value={newBankName}
                onChange={(e) => setNewBankName(e.target.value)}
                required
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                Register bank
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {banks.length > 0 ? (
        <div className="panel form-panel">
          <div className="panel-header">Statement import & reconciliation</div>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="bank-select">Bank account</label>
              <select
                id="bank-select"
                value={selectedBank}
                onChange={(e) => setSelectedBank(e.target.value)}
              >
                {banks.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                    {b.account_number ? ` (${b.account_number})` : ""}
                  </option>
                ))}
              </select>
            </div>
            {canWrite ? (
              <>
                <div className="form-field">
                  <label htmlFor="csv-file">Import CSV</label>
                  <input
                    id="csv-file"
                    type="file"
                    accept=".csv,text/csv"
                    disabled={busy}
                    onChange={(e) => handleImport(e.target.files?.[0] ?? null)}
                  />
                  <span className="field-hint">Columns: date, description, amount, reference</span>
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || !selectedBank}
                    onClick={handleReconcile}
                  >
                    Auto-reconcile
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      {loading ? <p>Loading…</p> : null}
    </>
  );
}
