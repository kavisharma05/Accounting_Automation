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
          Accounting Automation
          <span>{session.orgName}</span>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Overview
          </NavLink>
          <NavLink
            to="/invoices"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Invoices
          </NavLink>
          <NavLink
            to="/payments"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Payments
          </NavLink>
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
            to="/gstr"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            GSTR
          </NavLink>
          <NavLink
            to="/compliance"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            Compliance
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <div>{session.email}</div>
          <div>Role: {session.role}</div>
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
