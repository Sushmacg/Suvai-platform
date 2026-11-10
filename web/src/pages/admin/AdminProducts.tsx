import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../api/client";
import type { Product } from "../../api/models";
import { Label, inp } from "../../components/inputs";
import { ProductImage } from "../../components/ProductImage";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { rupees } from "../../utils/format";

type F = { name: string; category: string; price: string; description: string; image_url: string; is_available: boolean };
const EMPTY: F = { name: "", category: "Nankhatai", price: "", description: "", image_url: "", is_available: true };

export function AdminProducts() {
  const { data, loading, error, reload } = useLoad(() => api.get<Product[]>("/products/admin/all"), []);
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [f, setF] = useState<F>(EMPTY);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const items = data ?? [];

  function open(p: Product | "new") {
    setEditing(p);
    setMsg(null);
    setF(p === "new" ? EMPTY : { name: p.name, category: p.category, price: String(Number(p.price)), description: p.description ?? "", image_url: p.image_url ?? "", is_available: p.is_available });
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (f.name.trim().length < 2 || f.category.trim().length < 2) return setMsg({ kind: "error", text: "Name and category need at least 2 characters." });
    if (!(Number(f.price) > 0)) return setMsg({ kind: "error", text: "Enter a price above 0." });
    const body = { name: f.name.trim(), category: f.category.trim(), price: f.price, description: f.description.trim() || null, image_url: f.image_url.trim() || null, is_available: f.is_available };
    setBusy("form");
    setMsg(null);
    try {
      if (editing === "new") await api.post("/products", body);
      else if (editing) await api.patch(`/products/${editing.id}`, body);
      setEditing(null);
      setMsg({ kind: "success", text: "Product saved." });
      reload();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof Error ? err.message : "Could not save the product." });
    } finally {
      setBusy("");
    }
  }

  async function patch(p: Product, body: object, ok: string) {
    setBusy(p.id);
    setMsg(null);
    try {
      await api.patch(`/products/${p.id}`, body);
      setMsg({ kind: "success", text: ok });
      reload();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof Error ? err.message : "Update failed." });
    } finally {
      setBusy("");
    }
  }

  const set = <K extends keyof F>(k: K, v: F[K]) => setF((cur) => ({ ...cur, [k]: v }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Products</h1>
        {!editing && <Button onClick={() => open("new")}>Add product</Button>}
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}

      {editing && (
        <Card>
          <h2 className="mb-4 text-xl font-bold">{editing === "new" ? "New product" : `Edit ${editing.name}`}</h2>
          <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
            <Label text="Name"><input className={inp} value={f.name} maxLength={120} onChange={(e) => set("name", e.target.value)} required /></Label>
            <Label text="Category">
              <input className={inp} list="cats" value={f.category} maxLength={50} onChange={(e) => set("category", e.target.value)} required />
              <datalist id="cats">{[...new Set(items.map((p) => p.category))].map((c) => <option key={c} value={c} />)}</datalist>
            </Label>
            <Label text="Price (INR)"><input className={inp} inputMode="decimal" value={f.price} onChange={(e) => set("price", e.target.value)} required /></Label>
            <Label text="Image URL (optional, leave empty for the illustration)"><input className={inp} type="url" value={f.image_url} maxLength={500} onChange={(e) => set("image_url", e.target.value)} /></Label>
            <div className="md:col-span-2"><Label text="Description"><textarea className={inp} rows={3} value={f.description} onChange={(e) => set("description", e.target.value)} /></Label></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_available} onChange={(e) => set("is_available", e.target.checked)} /> Available to order</label>
            <div className="flex gap-3 md:col-span-2">
              <Button type="submit" disabled={busy === "form"}>{busy === "form" ? "Saving..." : "Save"}</Button>
              <Button type="button" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {loading && !data && <PageSpinner />}
      {error && <div className="space-y-3"><Notice>{error}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>}
      {data && items.length === 0 && <Card className="text-center text-muted">No products yet. Add the first one.</Card>}

      <ul className="space-y-3">
        {items.map((p) => (
          <li key={p.id}>
            <Card className={`flex flex-wrap items-center gap-4 p-4 ${p.is_active ? "" : "opacity-60"}`}>
              <ProductImage product={p} className="h-16 w-16 shrink-0 rounded-xl bg-saffron-soft p-1" />
              <div className="min-w-0 flex-1">
                <p className="font-bold">{p.name} {!p.is_active && <span className="ml-1 rounded-full bg-line px-2 py-0.5 text-xs font-medium text-muted">Archived</span>}</p>
                <p className="text-sm text-muted">{p.category} · {rupees(p.price)} · {p.is_available ? "Available" : "Unavailable"}</p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Button variant="ghost" onClick={() => open(p)}>Edit</Button>
                {p.is_active && <Button variant="ghost" disabled={busy === p.id} onClick={() => patch(p, { is_available: !p.is_available }, p.is_available ? "Marked unavailable." : "Marked available.")}>{p.is_available ? "Mark unavailable" : "Mark available"}</Button>}
                <Button variant="ghost" disabled={busy === p.id} onClick={() => patch(p, { is_active: !p.is_active }, p.is_active ? "Product archived." : "Product restored.")}>{p.is_active ? "Archive" : "Restore"}</Button>
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}