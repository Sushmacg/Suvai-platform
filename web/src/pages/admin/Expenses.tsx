import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../api/client";
import type { Expense, ExpenseSummary } from "../../api/adminModels";
import { Label, inp } from "../../components/inputs";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { isoDate } from "../../utils/dates";
import { dayLabel, rupees } from "../../utils/format";

const CATS = ["ingredients", "packaging", "fuel", "transport", "rent", "labour", "utilities", "marketing", "maintenance", "other"];
type F = { amount: string; category: string; description: string; expense_date: string };
const blank = (): F => ({ amount: "", category: "ingredients", description: "", expense_date: isoDate() });

export function Expenses() {
  const [cat, setCat] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const q = { ...(cat ? { category: cat } : {}), ...(start ? { start } : {}), ...(end ? { end } : {}) };
  const list = useLoad(() => api.get<Expense[]>("/expenses", { ...q, limit: 50 }), [cat, start, end]);
  const sum = useLoad(() => api.get<ExpenseSummary>("/expenses/summary", q), [cat, start, end]);
  const [editing, setEditing] = useState<Expense | "new" | null>(null);
  const [f, setF] = useState<F>(blank());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const set = <K extends keyof F>(k: K, v: F[K]) => setF((c) => ({ ...c, [k]: v }));

  function open(x: Expense | "new") {
    setEditing(x);
    setMsg(null);
    setF(x === "new" ? blank() : { amount: String(Number(x.amount)), category: x.category, description: x.description ?? "", expense_date: x.expense_date });
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!(Number(f.amount) > 0)) return setMsg({ kind: "error", text: "Enter an amount above 0." });
    const body = { amount: f.amount, category: f.category, description: f.description.trim() || null, expense_date: f.expense_date };
    setBusy(true);
    setMsg(null);
    try {
      if (editing === "new") await api.post("/expenses", body); else if (editing) await api.patch(`/expenses/${editing.id}`, body);
      setEditing(null);
      setMsg({ kind: "success", text: "Expense saved." });
      list.reload();
      sum.reload();
    } catch (x) {
      setMsg({ kind: "error", text: x instanceof Error ? x.message : "Could not save the expense." });
    } finally {
      setBusy(false);
    }
  }

  const items = list.data ?? [];
  const by = Object.entries(sum.data?.by_category ?? {}).map(([k, v]) => [k, Number(v)] as const).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...by.map(([, v]) => v), 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Expenses</h1>
        {!editing && <Button onClick={() => open("new")}>Add expense</Button>}
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}

      {editing && (
        <Card>
          <h2 className="mb-4 text-xl font-bold">{editing === "new" ? "New expense" : "Edit expense"}</h2>
          <form onSubmit={save} className="grid gap-4 md:grid-cols-4">
            <Label text="Amount (INR)"><input className={inp} inputMode="decimal" value={f.amount} onChange={(e) => set("amount", e.target.value)} required /></Label>
            <Label text="Category"><select className={inp} value={f.category} onChange={(e) => set("category", e.target.value)}>{CATS.map((c) => <option key={c} value={c}>{c}</option>)}</select></Label>
            <Label text="Date"><input type="date" className={inp} value={f.expense_date} onChange={(e) => set("expense_date", e.target.value)} required /></Label>
            <Label text="Description (optional)"><input className={inp} maxLength={500} value={f.description} onChange={(e) => set("description", e.target.value)} /></Label>
            <div className="flex gap-3 md:col-span-4">
              <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Save"}</Button>
              <Button type="button" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <Label text="Category"><select className={`${inp} w-auto`} value={cat} onChange={(e) => setCat(e.target.value)}><option value="">All</option>{CATS.map((c) => <option key={c} value={c}>{c}</option>)}</select></Label>
        <Label text="From"><input type="date" className={`${inp} w-auto`} value={start} onChange={(e) => setStart(e.target.value)} /></Label>
        <Label text="To"><input type="date" className={`${inp} w-auto`} value={end} onChange={(e) => setEnd(e.target.value)} /></Label>
        {(cat || start || end) && <Button variant="ghost" onClick={() => { setCat(""); setStart(""); setEnd(""); }}>Clear filters</Button>}
      </div>

      {(list.error || sum.error) && <Notice>{list.error || sum.error}</Notice>}
      {list.loading && !list.data && <PageSpinner />}

      {sum.data && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="p-4"><p className="text-xs font-semibold uppercase tracking-widest text-muted">Total</p><p className="mt-1 text-2xl font-bold">{rupees(sum.data.total)}</p><p className="text-sm text-muted">{sum.data.count} {sum.data.count === 1 ? "expense" : "expenses"}</p></Card>
          <Card className="p-4 md:col-span-2">
            {by.length === 0 ? <p className="text-muted">No expenses in this view.</p> : (
              <ul className="space-y-2">{by.map(([k, v]) => (
                <li key={k}>
                  <div className="flex justify-between text-sm"><span className="font-medium capitalize">{k}</span><span className="text-muted">{rupees(v)}</span></div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-terracotta" style={{ width: `${(v / max) * 100}%` }} /></div>
                </li>
              ))}</ul>
            )}
          </Card>
        </div>
      )}

      {list.data && items.length === 0 && <Card className="text-center text-muted">No expenses to show.</Card>}
      <ul className="space-y-3">
        {items.map((x) => (
          <li key={x.id}>
            <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-bold capitalize">{x.category}</p>
                <p className="text-sm text-muted">{dayLabel(x.expense_date)}{x.description ? ` · ${x.description}` : ""}</p>
              </div>
              <div className="flex items-center gap-3"><span className="text-lg font-bold">{rupees(x.amount)}</span><Button variant="ghost" onClick={() => open(x)}>Edit</Button></div>
            </Card>
          </li>
        ))}
      </ul>
      {items.length === 50 && <p className="text-xs text-muted">Showing the latest 50. Use the filters to narrow down.</p>}
    </div>
  );
}