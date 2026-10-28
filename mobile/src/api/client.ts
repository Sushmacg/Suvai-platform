import { API_BASE } from "../config";
import { clearTokens, loadTokens, saveTokens } from "./tokenStorage";
import type { TokenResponse } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const TIMEOUT_MS = 15000;

type Query = Record<string, string | number | boolean | null | undefined>;
interface Options {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Query;
  auth?: boolean; // default true; pass false for login, register and public calls
}

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

function buildUrl(path: string, query?: Query): string {
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join("&")
    : "";
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function parseError(res: Response): Promise<string> {
  try {
    const detail = (await res.json())?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((e) => e?.msg ?? "Invalid input").join("; ");
    }
  } catch {
    // body was not JSON
  }
  return `Request failed (${res.status})`;
}

async function send(path: string, opts: Options, token?: string): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const hasBody = opts.body !== undefined;
  try {
    return await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: hasBody ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new ApiError(0, "The server took too long to respond.");
    }
    throw new ApiError(0, "Could not reach the server. Check your Wi-Fi and the API address.");
  } finally {
    clearTimeout(timer);
  }
}

// One refresh at a time. Returns null only when the server rejects the refresh token;
// a network failure throws, so a bad connection never logs the user out.
let refreshing: Promise<string | null> | null = null;
function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = (async () => {
      const tokens = await loadTokens();
      if (!tokens) return null;
      const res = await send("/auth/refresh", { method: "POST", body: { refresh_token: tokens.refresh } });
      if (!res.ok) return null;
      const data = (await res.json()) as TokenResponse;
      await saveTokens({ access: data.access_token, refresh: data.refresh_token });
      return data.access_token;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const useAuth = opts.auth !== false;
  const tokens = useAuth ? await loadTokens() : null;
  let res = await send(path, opts, tokens?.access);

  if (res.status === 401 && tokens) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      res = await send(path, opts, fresh);
    } else {
      await clearTokens();
      onSessionExpired?.();
    }
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, opts: Omit<Options, "method" | "body"> = {}) =>
    request<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts: Omit<Options, "method" | "body"> = {}) =>
    request<T>(path, { ...opts, method: "POST", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};