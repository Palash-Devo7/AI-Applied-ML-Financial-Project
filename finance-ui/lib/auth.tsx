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

  // Restore token from localStorage on mount (shared across tabs)
  useEffect(() => {
    const saved = localStorage.getItem("auth_token");
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
        localStorage.removeItem("auth_token");
        setState({ token: null, user: null, credits: null, loading: false });
      });
  }, []);

  // Refresh user data when tab regains focus or receives verified signal from another tab
  useEffect(() => {
    const refresh = () => {
      if (state.token) {
        authMe()
          .then((me) => setState((s) => ({ ...s, user: me, credits: me.credits })))
          .catch(() => {});
      }
    };
    const handleVisibility = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", handleVisibility);

    let channel: BroadcastChannel | null = null;
    try {
      channel = new BroadcastChannel("auth");
      channel.onmessage = (e) => { if (e.data === "verified") refresh(); };
    } catch {}

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      channel?.close();
    };
  }, [state.token]);

  const login = useCallback(async (token: string) => {
    setAuthToken(token);
    localStorage.setItem("auth_token", token);
    const me = await authMe();
    setState({ token, user: me, credits: me.credits, loading: false });
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    localStorage.removeItem("auth_token");
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
