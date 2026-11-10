import { API_URL } from "../config";
import { clearTokens, getTokens, setTokens } from "./tokens";

const BASE = `${API_URL}/api/v1`;
export const SESSION_EXPIRED = "suvai:session-expired";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;
type Opts = { method?: string; body?: unknown; query?: Query; auth?: boolean };

function detailText(d: unknown): string {
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => (e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : "Invalid input")).join(". ");
  }
  return "Something went wrong.";
}

let refreshing: Promise<boolean> | null = null;
function refreshTokens(): Promise<boolean> {
  const t = getTokens();
  if (!t) return Promise.resolve(false);
  refreshing ??= (async () => {
    try {
      const r = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: t.refresh }),
      });
      if (!r.ok) return false;
      const j = (await r.json()) as { access_token: string; refresh_token: string };
      setTokens({ access: j.access_token, refresh: j.refresh_token });
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

const OFFLINE = "Cannot reach the server. Check that the backend is running.";

export async function request<T>(path: string, opts: Opts = {}): Promise<T> {
  const { method = "GET", body, query, auth = true } = opts;
  const qs = query
    ? "?" + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null).map(([k, v]) => [k, String(v)])).toString()
    : "";
  const send = () => {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const t = getTokens();
    if (auth && t) headers.Authorization = `Bearer ${t.access}`;
    return fetch(`${BASE}${path}${qs}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  };

  let res: Response;
  try {
    res = await send();
  } catch {
    throw new ApiError(0, OFFLINE);
  }
  if (res.status === 401 && auth && getTokens()) {
    if (await refreshTokens()) {
      try { res = await send(); } catch { throw new ApiError(0, OFFLINE); }
    } else {
      clearTokens();
      window.dispatchEvent(new Event(SESSION_EXPIRED));
    }
  }
  if (!res.ok) {
    let msg = "Request failed.";
    try { msg = detailText(((await res.json()) as { detail?: unknown }).detail); } catch { /* no body */ }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: Query, auth = true) => request<T>(path, { query, auth }),
  post: <T>(path: string, body?: unknown, auth = true) => request<T>(path, { method: "POST", body, auth }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};