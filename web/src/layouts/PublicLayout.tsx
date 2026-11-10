import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { btn } from "../components/ui";
import { useCart } from "../cart/CartContext";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3 py-1.5 text-sm font-medium transition ${isActive ? "bg-saffron-soft text-terracotta-dark" : "text-ink hover:bg-saffron-soft"}`;

export function PublicLayout() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  const links = (
    <>
      <NavLink to="/" end className={link} onClick={close}>Home</NavLink>
      <NavLink to="/menu" className={link} onClick={close}>Menu</NavLink>
      <NavLink to="/stalls" className={link} onClick={close}>Stalls</NavLink>
      <NavLink to="/cart" className={link} onClick={close}>Cart{count > 0 ? ` (${count})` : ""}</NavLink>
      {user?.role === "customer" && <NavLink to="/orders" className={link} onClick={close}>My orders</NavLink>}
      {user?.role === "admin" && <NavLink to="/admin" className={link} onClick={close}>Admin</NavLink>}
    </>
  );

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-cream/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-display text-2xl font-bold text-terracotta">
            Suvai <span className="text-sm font-semibold tracking-[0.3em] text-ink">NANKATAI</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{links}</nav>
          <div className="hidden items-center gap-2 md:flex">
            {user ? (
              <>
                <span className="text-sm text-muted">Hi, {user.name.split(" ")[0]}</span>
                <button className={btn("ghost")} onClick={() => logout().then(() => nav("/"))}>Log out</button>
              </>
            ) : (
              <>
                <Link to="/login" className={btn("ghost")}>Log in</Link>
                <Link to="/register" className={btn()}>Sign up</Link>
              </>
            )}
          </div>
          <button className="rounded-lg p-2 md:hidden" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            <span className="block h-0.5 w-6 bg-ink" /><span className="mt-1.5 block h-0.5 w-6 bg-ink" /><span className="mt-1.5 block h-0.5 w-6 bg-ink" />
          </button>
        </div>
        {open && (
          <div className="flex flex-col gap-1 border-t border-line px-4 pb-4 pt-2 md:hidden">
            {links}
            {user ? (
              <button className={btn("ghost", "mt-2")} onClick={() => { close(); logout().then(() => nav("/")); }}>Log out</button>
            ) : (
              <div className="mt-2 flex gap-2">
                <Link to="/login" className={btn("ghost", "flex-1")} onClick={close}>Log in</Link>
                <Link to="/register" className={btn("primary", "flex-1")} onClick={close}>Sign up</Link>
              </div>
            )}
          </div>
        )}
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t border-line bg-surface py-8 text-center text-sm text-muted">
        <p className="font-display text-lg text-terracotta">Suvai Nankatai</p>
        <p>Homemade with love. Pure butter, small batches, freshly baked.</p>
      </footer>
    </div>
  );
}