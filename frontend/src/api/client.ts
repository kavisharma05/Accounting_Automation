const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

export type AuthSession = {
  token: string;
  orgId: string;
  role: string;
  email: string;
  orgName: string;
};

export type DashboardSummary = {
  pending_approvals: number;
  outstanding_invoices_count: number;
  outstanding_total: string;
  recent_journal_entries: {
    id: string;
    entry_number: string;
    entry_date: string;
    description: string;
  }[];
};

export type InvoiceRow = {
  id: string;
  invoice_number: string;
  invoice_date: string;
  invoice_type?: string;
  party_id?: string;
  party_name?: string;
  total: string;
  status: string;
  outstanding: string;
};

export type PaymentRow = {
  id: string;
  amount: string;
  payment_date: string;
  reference: string | null;
  journal_entry_id: string | null;
};

export type PartyRow = {
  id: string;
  name: string;
  party_type: string;
  gstin: string | null;
};

export type AccountRow = {
  id: string;
  code: string;
  name: string;
  account_type: string;
};

export type BankAccountRow = {
  id: string;
  name: string;
  account_number: string | null;
  chart_of_account_id: string;
};

export type PilotConfig = {
  organization_id: string;
  default_expense_account_id: string | null;
  default_payable_account_id: string | null;
  default_input_tax_account_id: string | null;
  default_receivable_account_id: string | null;
  default_revenue_account_id: string | null;
  default_output_tax_account_id: string | null;
};

export type Gstr3bSummary = {
  period_start: string;
  period_end: string;
  outward_taxable_supplies: number;
  output_tax: number;
  input_tax_credit: number;
  net_tax_payable: number;
  sales_invoice_count: number;
  purchase_invoice_count: number;
};

export type MeResponse = {
  user_id: string;
  email: string;
  organization_id: string;
  organization_name: string;
  role: string;
};

export type PaymentCreatePayload = {
  party_id: string;
  amount: string;
  payment_date: string;
  payable_account_id: string;
  bank_account_id: string;
  reference?: string;
  applications?: { invoice_id: string; amount_applied: string }[];
};

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const isForm = options.body instanceof FormData;
  if (!isForm) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, String(detail));
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  const text = await resp.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export async function login(email: string, password: string): Promise<string> {
  const data = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return data.access_token;
}

export async function fetchMe(token: string): Promise<MeResponse> {
  return request<MeResponse>("/me", {}, token);
}

export async function fetchDashboard(
  orgId: string,
  token: string,
): Promise<DashboardSummary> {
  return request<DashboardSummary>(
    `/organizations/${orgId}/dashboard`,
    {},
    token,
  );
}

export async function fetchInvoices(
  orgId: string,
  token: string,
  status?: string,
): Promise<InvoiceRow[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<InvoiceRow[]>(
    `/organizations/${orgId}/invoices${qs}`,
    {},
    token,
  );
}

export async function searchInvoices(
  orgId: string,
  token: string,
  q: string,
): Promise<InvoiceRow[]> {
  return request<InvoiceRow[]>(
    `/organizations/${orgId}/search/invoices?q=${encodeURIComponent(q)}`,
    {},
    token,
  );
}

export async function fetchPayments(
  orgId: string,
  token: string,
): Promise<PaymentRow[]> {
  return request<PaymentRow[]>(
    `/organizations/${orgId}/payments`,
    {},
    token,
  );
}

export async function fetchParties(orgId: string, token: string): Promise<PartyRow[]> {
  return request<PartyRow[]>(`/organizations/${orgId}/parties`, {}, token);
}

export async function fetchAccounts(orgId: string, token: string): Promise<AccountRow[]> {
  return request<AccountRow[]>(`/organizations/${orgId}/accounts`, {}, token);
}

export async function fetchBankAccounts(
  orgId: string,
  token: string,
): Promise<BankAccountRow[]> {
  return request<BankAccountRow[]>(
    `/organizations/${orgId}/bank-accounts`,
    {},
    token,
  );
}

export async function fetchPilotConfig(
  orgId: string,
  token: string,
): Promise<PilotConfig> {
  return request<PilotConfig>(`/organizations/${orgId}/pilot-config`, {}, token);
}

export async function createPayment(
  orgId: string,
  token: string,
  payload: PaymentCreatePayload,
): Promise<PaymentRow> {
  return request<PaymentRow>(
    `/organizations/${orgId}/payments`,
    { method: "POST", body: JSON.stringify(payload) },
    token,
  );
}

export async function createBankAccount(
  orgId: string,
  token: string,
  body: { name: string; chart_of_account_id: string; account_number?: string },
): Promise<BankAccountRow> {
  return request<BankAccountRow>(
    `/organizations/${orgId}/bank-accounts`,
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
}

export async function importBankCsv(
  orgId: string,
  token: string,
  bankId: string,
  file: File,
): Promise<{ imported: number }> {
  const form = new FormData();
  form.append("file", file);
  return request<{ imported: number }>(
    `/organizations/${orgId}/bank-accounts/${bankId}/import`,
    { method: "POST", body: form },
    token,
  );
}

export async function reconcileBank(
  orgId: string,
  token: string,
  bankId: string,
): Promise<{ matches: number }> {
  return request<{ matches: number }>(
    `/organizations/${orgId}/bank-accounts/${bankId}/reconcile`,
    { method: "POST" },
    token,
  );
}

export async function fetchGstr3b(
  orgId: string,
  token: string,
  periodStart: string,
  periodEnd: string,
): Promise<Gstr3bSummary> {
  return request<Gstr3bSummary>(
    `/organizations/${orgId}/gstr/gstr3b?period_start=${periodStart}&period_end=${periodEnd}`,
    {},
    token,
  );
}

export async function downloadLedger(orgId: string, token: string): Promise<Blob> {
  const resp = await fetch(
    `${API_BASE}/organizations/${orgId}/reports/ledger.xlsx`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!resp.ok) {
    throw new ApiError(resp.status, "Failed to download ledger");
  }
  return resp.blob();
}

export async function downloadGstr1(
  orgId: string,
  token: string,
  periodStart: string,
  periodEnd: string,
): Promise<Blob> {
  const resp = await fetch(
    `${API_BASE}/organizations/${orgId}/reports/gstr1.xlsx?period_start=${periodStart}&period_end=${periodEnd}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!resp.ok) {
    throw new ApiError(resp.status, "Failed to download GSTR-1");
  }
  return resp.blob();
}

export { ApiError };
