import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Field, Notice } from "../components/ui";

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", phone: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (f.name.trim().length < 2) return setError("Enter your name (at least 2 characters).");
    if (!/^\d{10,15}$/.test(f.phone.trim())) return setError("Phone must be 10 to 15 digits.");
    if (f.password.length < 8) return setError("Password must be at least 8 characters.");
    setBusy(true);
    try {
      await register({ name: f.name.trim(), phone: f.phone.trim(), email: f.email.trim(), password: f.password });
      nav("/menu", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card>
        <h1 className="text-3xl font-bold">Create your account</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {error && <Notice>{error}</Notice>}
          <Field label="Name" autoComplete="name" required value={f.name} onChange={set("name")} />
          <Field label="Phone" type="tel" inputMode="tel" autoComplete="username" required value={f.phone} onChange={set("phone")} />
          <Field label="Email (optional)" type="email" autoComplete="email" value={f.email} onChange={set("email")} />
          <Field label="Password" type="password" autoComplete="new-password" required value={f.password} onChange={set("password")} />
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Creating..." : "Sign up"}</Button>
        </form>
        <p className="mt-4 text-sm text-muted">Already registered? <Link to="/login" className="font-semibold text-terracotta">Log in</Link></p>
      </Card>
    </div>
  );
}