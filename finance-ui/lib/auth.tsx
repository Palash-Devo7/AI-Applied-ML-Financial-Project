"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  ReactNode,
} from "react";
import { setAuthToken, clearAuthToken, authMe, type AuthUser, type Credits } from "./api";

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  credits: Credits | null;
  loading: boolean;
}

interface AuthContextType extends AuthState {
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshCredits: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    credits: null,
    loading: true,
  });

  // Restore token from sessionStorage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem("auth_token");
    if (!saved) {
      setState((s) => ({ ...s, loading: false }));
      return;
    }
    setAuthToken(saved);
    authMe()
      .then((me) =>
        setState({ token: saved, user: me, credits: me.credits, loading: false })
      )
      .catch(() => {
        clearAuthToken();
        sessionStorage.removeItem("auth_token");
        setState({ token: null, user: null, credits: null, loading: false });
      });
  }, []);

  const login = useCallback(async (token: string) => {
    setAuthToken(token);
    sessionStorage.setItem("auth_token", token);
    const me = await authMe();
    setState({ token, user: me, credits: me.credits, loading: false });
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    sessionStorage.removeItem("auth_token");
    setState({ token: null, user: null, credits: null, loading: false });
  }, []);

  const refreshCredits = useCallback(async () => {
    if (!state.token) return;
    const me = await authMe();
    setState((s) => ({ ...s, credits: me.credits }));
  }, [state.token]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshCredits }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
