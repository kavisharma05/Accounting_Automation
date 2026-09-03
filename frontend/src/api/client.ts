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

export type MeResponse = {
  user_id: string;
  email: string;
  organization_id: string;
  organization_name: string;
  role: string;
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
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
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

export { ApiError };
