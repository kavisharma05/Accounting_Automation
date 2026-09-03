import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { AuthSession } from "../api/client";

const STORAGE_KEY = "accounting_auth";

type AuthContextValue = {
  session: AuthSession | null;
  setSession: (session: AuthSession | null) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function loadSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthSession) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AuthSession | null>(loadSession);

  const setSession = (next: AuthSession | null) => {
    if (next) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setSessionState(next);
  };

  const value = useMemo(
    () => ({
      session,
      setSession,
      logout: () => setSession(null),
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
