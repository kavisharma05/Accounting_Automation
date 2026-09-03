import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { BankPage } from "./pages/BankPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CompliancePage } from "./pages/CompliancePage";
import { GstrPage } from "./pages/GstrPage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { LoginPage } from "./pages/LoginPage";
import { NotesPage } from "./pages/NotesPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import { SalesPage } from "./pages/SalesPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="sales" element={<SalesPage />} />
        <Route path="notes" element={<NotesPage />} />
        <Route path="bank" element={<BankPage />} />
        <Route path="gstr" element={<GstrPage />} />
        <Route path="compliance" element={<CompliancePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
