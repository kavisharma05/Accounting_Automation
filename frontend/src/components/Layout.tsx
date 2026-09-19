import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { session, logout } = useAuth();
  if (!session) {
    return null;
  }

  const canWrite = session.role === "owner" || session.role === "accountant" || session.role === "admin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          Books
          <span>Photo in. Confirm. Done.</span>
        </div>
        <nav>
          <div className="nav-label">Your day</div>
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Home
          </NavLink>
          <NavLink
            to="/invoices"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Bills
          </NavLink>
          <NavLink
            to="/payments"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Pay
          </NavLink>
          <NavLink
            to="/reports"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Reports
          </NavLink>
          <details className="nav-more">
            <summary>Accountant tools</summary>
            <NavLink
              to="/sales"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              Sales
            </NavLink>
            <NavLink
              to="/notes"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              Notes
            </NavLink>
            <NavLink
              to="/bank"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              Bank
            </NavLink>
            <NavLink
              to="/compliance"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              Compliance
            </NavLink>
          </details>
        </nav>
        <div className="sidebar-footer">
          <div>{session.orgName}</div>
          <div>{session.email}</div>
          {!canWrite ? <div className="muted-hint">Read-only access</div> : null}
          <button type="button" className="btn btn-secondary" onClick={logout} style={{ marginTop: "0.75rem" }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
