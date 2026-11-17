import type { ReactNode } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { NankhataiArt } from "../components/NankhataiArt";

const Icon = ({ children }: { children: ReactNode }) => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

type Item = { to: string; label: string; end: boolean; icon: ReactNode };
const items: Item[] = [
  { to: "/admin", label: "Dashboard", end: true, icon: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></> },
  { to: "/admin/products", label: "Products", end: false, icon: <><path d="M21 8 12 3 3 8v8l9 5 9-5V8Z" /><path d="m3 8 9 5 9-5M12 13v8" /></> },
  { to: "/admin/orders", label: "Orders", end: false, icon: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4h6v3H9zM9 12h6M9 16h4" /></> },
  { to: "/admin/inventory", label: "Inventory", end: false, icon: <><path d="M12 3 3 8l9 5 9-5-9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></> },
  { to: "/admin/stalls", label: "Stalls and sessions", end: false, icon: <><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></> },
  { to: "/admin/expenses", label: "Expenses", end: false, icon: <><path d="M3 7a2 2 0 0 1 2-2h13v4" /><rect x="3" y="7" width="18" height="13" rx="2" /><circle cx="16.5" cy="13.5" r="1.2" /></> },
  { to: "/admin/forecast", label: "Forecast", end: false, icon: <><path d="m3 17 6-6 4 4 8-8" /><path d="M15 7h6v6" /></> },
  { to: "/admin/reviews", label: "Reviews", end: false, icon: <path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3Z" /> },
  { to: "/admin/assistant", label: "Assistant", end: false, icon: <><path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-6l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" /><path d="M8 10h8M8 13h5" /></> },
];

const base = "group relative flex h-11 w-11 items-center justify-center rounded-xl transition";
const idle = "text-muted hover:bg-saffron-soft hover:text-terracotta-dark";

const Tip = ({ label }: { label: string }) => (
  <span aria-hidden="true" className="pointer-events-none absolute left-full z-30 ml-3 whitespace-nowrap rounded-lg bg-ink px-2.5 py-1 text-xs font-medium text-white opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-visible:opacity-100">{label}</span>
);

export function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-16 shrink-0 flex-col items-center gap-2 border-r border-line bg-surface py-4">
        <Link to="/admin" aria-label="Suvai admin home" className="mb-3"><NankhataiArt name="Classic Nankhatai" className="h-9 w-9" /></Link>
        <nav className="flex flex-col items-center gap-2" aria-label="Admin">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} aria-label={i.label} title={i.label}
              className={({ isActive }) => `${base} ${isActive ? "bg-terracotta text-white shadow-md" : idle}`}>
              <Icon>{i.icon}</Icon>
              <Tip label={i.label} />
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex flex-col items-center gap-2">
          <Link to="/" aria-label="View website" title="View website" className={`${base} ${idle}`}>
            <Icon><path d="m3 11 9-7 9 7" /><path d="M5 10v10h14V10M10 20v-5h4v5" /></Icon>
            <Tip label="View website" />
          </Link>
          <button type="button" aria-label="Log out" title="Log out" className={`${base} ${idle}`} onClick={() => logout().then(() => nav("/login"))}>
            <Icon><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" /><path d="m16 8 4 4-4 4M20 12H9" /></Icon>
            <Tip label="Log out" />
          </button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-between border-b border-line bg-cream px-4 py-3">
          <span className="font-display text-lg font-bold text-terracotta">Suvai Admin</span>
          <span className="text-sm text-muted">{user?.name}</span>
        </header>
        <main className="p-4 md:p-8"><Outlet /></main>
      </div>
    </div>
  );
}