import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Field, Notice } from "../components/ui";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = await login(phone.trim(), password);
      const from = (loc.state as { from?: string } | null)?.from;
      nav(u.role === "admin" ? "/admin" : from ?? "/menu", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card>
        <h1 className="text-3xl font-bold">Welcome back</h1>
        <p className="mt-1 text-sm text-muted">Log in with your phone number.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {error && <Notice>{error}</Notice>}
          <Field label="Phone" type="tel" inputMode="tel" autoComplete="username" required value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Field label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Logging in..." : "Log in"}</Button>
        </form>
        <p className="mt-4 text-sm text-muted">New here? <Link to="/register" className="font-semibold text-terracotta">Create an account</Link></p>
      </Card>
    </div>
  );
}