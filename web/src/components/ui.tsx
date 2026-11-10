import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "ghost";

export const btn = (variant: Variant = "primary", extra = "") =>
  [
    "inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-terracotta",
    "disabled:cursor-not-allowed disabled:opacity-50",
    variant === "primary" ? "bg-terracotta text-white hover:bg-terracotta-dark" : "border border-line bg-white text-ink hover:bg-saffron-soft",
    extra,
  ].join(" ");

export function Button({ variant = "primary", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button {...p} className={btn(variant, className)} />;
}

export function Field({ label, error, ...p }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input {...p} className="w-full rounded-xl border border-line bg-white px-3 py-2.5 outline-none focus:border-terracotta focus:ring-2 focus:ring-saffron/40" />
      {error && <span className="mt-1 block text-bad">{error}</span>}
    </label>
  );
}

export function Notice({ kind = "error", children }: { kind?: "error" | "success"; children: ReactNode }) {
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-xl px-4 py-3 text-sm ${kind === "error" ? "bg-bad/10 text-bad" : "bg-ok/10 text-ok"}`}>
      {children}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-white p-6 shadow-sm ${className}`}>{children}</div>;
}

export function Spinner() {
  return <div role="status" aria-label="Loading" className="h-8 w-8 animate-spin rounded-full border-4 border-saffron-soft border-t-terracotta" />;
}

export function PageSpinner() {
  return <div className="flex min-h-[40vh] items-center justify-center"><Spinner /></div>;
}