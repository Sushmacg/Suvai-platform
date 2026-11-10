import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, SESSION_EXPIRED } from "../api/client";
import { clearTokens, getTokens, setTokens } from "../api/tokens";
import type { TokenResponse, User } from "../api/types";

type RegisterInput = { name: string; phone: string; email?: string; password: string };
type Auth = {
  user: User | null;
  loading: boolean;
  login: (phone: string, password: string) => Promise<User>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => Promise<void>;
};

const Ctx = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => getTokens() !== null);

  useEffect(() => {
    if (!getTokens()) return;
    api.get<User>("/users/me").then(setUser).catch(() => clearTokens()).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener(SESSION_EXPIRED, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED, onExpired);
  }, []);

  const login = useCallback(async (phone: string, password: string) => {
    const t = await api.post<TokenResponse>("/auth/login", { phone, password }, false);
    setTokens({ access: t.access_token, refresh: t.refresh_token });
    const me = await api.get<User>("/users/me");
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    await api.post("/auth/register", { ...input, email: input.email || undefined }, false);
    return login(input.phone, input.password);
  }, [login]);

  const logout = useCallback(async () => {
    const t = getTokens();
    if (t) await api.post("/auth/logout", { refresh_token: t.refresh }, false).catch(() => undefined);
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): Auth {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}