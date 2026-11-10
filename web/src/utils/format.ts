import { API_URL } from "../config";

export const rupees = (v: string | number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(Number(v));
export const dayLabel = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
export const timeRange = (s: string, e: string) => `${s.slice(0, 5)} - ${e.slice(0, 5)}`;
export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
export const mapsLink = (lat: number, lng: number) => `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
export const directionsLink = (lat: number, lng: number) => `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
export const imageUrl = (u: string | null) => (u ? (u.startsWith("/") ? `${API_URL}${u}` : u) : null);

export const statusStyle: Record<string, string> = {
  pending: "bg-saffron-soft text-terracotta-dark",
  confirmed: "bg-saffron-soft text-terracotta-dark",
  preparing: "bg-saffron/25 text-terracotta-dark",
  ready: "bg-ok/15 text-ok",
  completed: "bg-ok/15 text-ok",
  cancelled: "bg-bad/10 text-bad",
  open: "bg-ok/15 text-ok",
  scheduled: "bg-saffron-soft text-terracotta-dark",
  closed: "bg-line text-muted",
};