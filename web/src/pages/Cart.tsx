import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CurrentStall, Order, StallSession, StockItem } from "../api/models";
import { useAuth } from "../auth/AuthContext";
import { useCart } from "../cart/CartContext";
import { Stepper } from "../components/Stepper";
import { Button, Card, Notice, PageSpinner, btn } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { dayLabel, rupees, timeRange } from "../utils/format";

export function Cart() {
  const { lines, setQty, remove, clear, total } = useCart();
  const { user } = useAuth();
  const nav = useNavigate();
  const [sid, setSid] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const sessions = useLoad(async () => {
    const [cur, today, up] = await Promise.all([
      api.get<CurrentStall>("/stalls/current", undefined, false),
      api.get<StallSession[]>("/stalls/today", undefined, false),
      api.get<StallSession[]>("/stalls/upcoming", { days: 7 }, false),
    ]);
    const all = [cur.session, ...today, ...up].filter((s): s is StallSession => !!s && (s.status === "open" || s.status === "scheduled"));
    return [...new Map(all.map((s) => [s.id, s])).values()];
  }, []);
  const list = sessions.data ?? [];
  const chosen = sid || list.find((s) => s.status === "open")?.id || list[0]?.id || "";

  const stock = useLoad(() => (chosen ? api.get<StockItem[]>(`/inventory/sessions/${chosen}`, undefined, false) : Promise.resolve([] as StockItem[])), [chosen]);
  const avail = new Map((stock.data ?? []).map((s) => [s.product_id, s]));
  const problem = (productId: string, qty: number) => {
    const st = avail.get(productId);
    if (!st || !st.in_stock) return "Not stocked for this stall";
    return qty > st.available_qty ? `Only ${st.available_qty} left` : "";
  };
  const blocked = !chosen || stock.loading || lines.some((l) => problem(l.productId, l.qty));

  async function place() {
    setBusy(true);
    setError("");
    try {
      const o = await api.post<Order>("/orders", {
        session_id: chosen,
        items: lines.map((l) => ({ product_id: l.productId, quantity: l.qty })),
        notes: notes.trim() || undefined,
      });
      clear();
      nav(`/orders/${o.id}`, { state: { placed: true } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not place the order.");
    } finally {
      setBusy(false);
    }
  }

  if (lines.length === 0) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 text-center">
        <h1 className="text-4xl font-bold">Your cart is empty</h1>
        <p className="mt-2 text-muted">Pick something from the menu.</p>
        <Link to="/menu" className={btn("primary", "mt-6")}>View the menu</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-4xl font-bold">Your cart</h1>
      <div className="mt-6 grid gap-6 md:grid-cols-5">
        <div className="space-y-3 md:col-span-3">
          {lines.map((l) => {
            const warn = chosen && !stock.loading ? problem(l.productId, l.qty) : "";
            return (
              <Card key={l.productId} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-bold">{l.name}</p>
                  <p className="text-sm text-muted">{rupees(l.price)} each</p>
                  {warn && <p className="mt-1 text-sm font-medium text-bad">{warn}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <Stepper value={l.qty} onChange={(v) => setQty(l.productId, v)} />
                  <span className="w-20 text-right font-semibold">{rupees(Number(l.price) * l.qty)}</span>
                  <button className="text-sm text-bad underline" onClick={() => remove(l.productId)}>Remove</button>
                </div>
              </Card>
            );
          })}
        </div>

        <Card className="space-y-4 md:col-span-2">
          <h2 className="text-xl font-bold">Pick up at</h2>
          {sessions.loading && !sessions.data && <PageSpinner />}
          {sessions.error && <Notice>{sessions.error}</Notice>}
          {sessions.data && list.length === 0 && <Notice>There is no open or scheduled stall to order from right now. Please check back later.</Notice>}
          <div className="space-y-2">
            {list.map((s) => (
              <label key={s.id} className={`block cursor-pointer rounded-xl border p-3 text-sm ${chosen === s.id ? "border-terracotta bg-saffron-soft" : "border-line"}`}>
                <input type="radio" name="session" className="mr-2" checked={chosen === s.id} onChange={() => setSid(s.id)} />
                <span className="font-semibold">{s.location.name}</span>
                <span className="block pl-6 text-muted">{dayLabel(s.session_date)} · {timeRange(s.start_time, s.end_time)} · {s.status}</span>
              </label>
            ))}
          </div>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Note for the stall (optional)</span>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={300} rows={2} className="w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-terracotta focus:ring-2 focus:ring-saffron/40" />
          </label>
          <div className="flex items-center justify-between border-t border-line pt-4 text-lg font-bold"><span>Total</span><span>{rupees(total)}</span></div>
          <p className="text-xs text-muted">The final total is confirmed by the stall. Pay when you collect your order.</p>
          {error && <Notice>{error}</Notice>}
          {user ? (
            <Button className="w-full" disabled={busy || blocked} onClick={place}>{busy ? "Placing order..." : "Place order"}</Button>
          ) : (
            <Link to="/login" state={{ from: "/cart" }} className={btn("primary", "w-full")}>Log in to order</Link>
          )}
        </Card>
      </div>
    </div>
  );
}