const raw = (process.env.EXPO_PUBLIC_API_URL ?? "").trim();

export const API_URL = raw.replace(/\/+$/, "");
export const API_BASE = `${API_URL}/api/v1`;

export function apiConfigProblem(): string | null {
  if (!API_URL) {
    return "EXPO_PUBLIC_API_URL is not set. Create mobile/.env and restart Expo with --clear.";
  }
  if (/^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/i.test(API_URL)) {
    return "The API address points at localhost, which on a phone means the phone itself. Use your laptop's Wi-Fi IPv4 address.";
  }
  return null;
}
