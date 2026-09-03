import { type FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError, fetchMe, login } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { session, setSession } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@pilot.local");
  const [password, setPassword] = useState("pilot-admin-change-me");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (session) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(email, password);
      const me = await fetchMe(token);
      setSession({
        token,
        orgId: me.organization_id,
        role: me.role,
        email: me.email,
        orgName: me.organization_name,
      });
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Sign in</h1>
        <p>Indian SMB accounting dashboard</p>
        {error ? <div className="error-banner">{error}</div> : null}
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
