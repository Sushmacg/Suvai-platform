import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError, setSessionExpiredHandler } from "../api/client";
import { clearTokens, loadTokens, saveTokens } from "../api/tokenStorage";
import type { LoginRequest, RegisterRequest, TokenResponse, User } from "../api/types";

export type AuthStatus = "loading" | "signedOut" | "signedIn" | "unreachable";

interface AuthValue {
  status: AuthStatus;
  user: User | null;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);

  const restore = useCallback(async () => {
    setStatus("loading");
    const tokens = await loadTokens();
    if (!tokens) {
      setStatus("signedOut");
      return;
    }
    try {
      setUser(await api.get<User>("/users/me"));
      setStatus("signedIn");
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        setStatus("unreachable"); // offline: keep the tokens and let the user retry
      } else {
        await clearTokens();
        setUser(null);
        setStatus("signedOut");
      }
    }
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null);
      setStatus("signedOut");
    });
    restore();
    return () => setSessionExpiredHandler(null);
  }, [restore]);

  const login = useCallback(async (data: LoginRequest) => {
    const tokens = await api.post<TokenResponse>("/auth/login", data, { auth: false });
    await saveTokens({ access: tokens.access_token, refresh: tokens.refresh_token });
    try {
      setUser(await api.get<User>("/users/me"));
      setStatus("signedIn");
    } catch (e) {
      await clearTokens();
      throw e;
    }
  }, []);

  const register = useCallback(
    async (data: RegisterRequest) => {
      await api.post("/auth/register", { ...data, email: data.email?.trim() || null }, { auth: false });
      await login({ phone: data.phone, password: data.password });
    },
    [login],
  );

  const logout = useCallback(async () => {
    const tokens = await loadTokens();
    if (tokens) {
      try {
        await api.post("/auth/logout", { refresh_token: tokens.refresh }, { auth: false });
      } catch {
        // the local sign-out below still happens
      }
    }
    await clearTokens();
    setUser(null);
    setStatus("signedOut");
  }, []);

  const value = useMemo(
    () => ({ status, user, login, register, logout, retry: restore }),
    [status, user, login, register, logout, restore],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
