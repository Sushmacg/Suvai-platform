import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { btn } from "../components/ui";

const items = [
  ["/admin", "Dashboard", true],
  ["/admin/products", "Products", false],
  ["/admin/orders", "Orders", false],
  ["/admin/inventory", "Inventory", false],
  ["/admin/stalls", "Stalls and sessions", false],
  ["/admin/expenses", "Expenses", false],
  ["/admin/forecast", "Forecast", false],
  ["/admin/reviews", "Reviews", false],
  ["/admin/assistant", "Assistant", false],
] as const;

const link = ({ isActive }: { isActive: boolean }) =>
  `block rounded-xl px-3 py-2 text-sm font-medium transition ${isActive ? "bg-terracotta text-white" : "text-ink hover:bg-saffron-soft"}`;

export function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen md:flex">
      <aside className={`${open ? "block" : "hidden"} border-b border-line bg-surface p-4 md:block md:w-60 md:border-b-0 md:border-r`}>
        <Link to="/admin" className="mb-4 block font-display text-xl font-bold text-terracotta">Suvai Admin</Link>
        <nav className="space-y-1" aria-label="Admin">
          {items.map(([to, label, end]) => (
            <NavLink key={to} to={to} end={end} className={link} onClick={() => setOpen(false)}>{label}</NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1">
        <header className="flex items-center justify-between border-b border-line bg-cream px-4 py-3">
          <button className="rounded-lg border border-line px-3 py-1.5 text-sm md:hidden" aria-expanded={open} onClick={() => setOpen(!open)}>Menu</button>
          <Link to="/" className="text-sm text-muted hover:text-terracotta">View website</Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:inline">{user?.name}</span>
            <button className={btn("ghost")} onClick={() => logout().then(() => nav("/login"))}>Log out</button>
          </div>
        </header>
        <main className="p-4 md:p-8"><Outlet /></main>
      </div>
    </div>
  );
}