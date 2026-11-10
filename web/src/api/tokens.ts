import type { Tokens } from "./types";

const KEY = "suvai.tokens";

export function getTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}
export function setTokens(t: Tokens) {
  try { localStorage.setItem(KEY, JSON.stringify(t)); } catch { /* storage unavailable */ }
}
export function clearTokens() {
  try { localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
}