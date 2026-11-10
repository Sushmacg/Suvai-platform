import { useState } from "react";
import { api } from "../../api/client";
import type { StockAdmin } from "../../api/adminModels";
import type { Product, StallSession } from "../../api/models";
import { inp } from "../../components/inputs";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { addDays, isoDate } from "../../utils/dates";
import { dayLabel } from "../../utils/format";

type Msg = { kind: "error" | "success"; text: string };
const whole = (v: string) => /^\d+$/.test(v.trim());

function Row({ p, st, sid, done, fail }: { p: Product; st?: StockAdmin; sid: string; done: (m: string) => void; fail: (m: string) => void }) {
  const [qty, setQty] = useState(st ? String(st.stocked_qty) : "");
  const [min, setMin] = useState(st ? String(st.min_stock) : "");
  const [waste, setWaste] = useState("");
  const [busy, setBusy] = useState(false);
  const base = `/inventory/sessions/${sid}/products/${p.id}`;

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try { await fn(); done(ok); } catch (e) { fail(e instanceof Error ? e.message : "Request failed."); } finally { setBusy(false); }
  }
  const save = () => {
    if (!whole(qty) || (min !== "" && !whole(min))) return fail("Stock and minimum must be whole numbers.");
    run(() => api.put(base, { stocked_qty: Number(qty), min_stock: min === "" ? null : Number(min) }), `Stock saved for ${p.name}.`);
  };
  const logWaste = () => {
    if (!whole(waste) || Number(waste) < 1) return fail("Waste must be a whole number above 0.");
    run(() => api.post(`${base}/waste`, { quantity: Number(waste) }), `Waste logged for ${p.name}.`);
  };
  const num = "w-20 rounded-lg border border-line bg-white px-2 py-1.5 text-sm";

  return (
    <tr className="border-t border-line align-top text-sm">
      <td className="py-3 pr-3 font-medium">{p.name}{st?.is_low_stock && <span className="ml-2 rounded-full bg-bad/10 px-2 py-0.5 text-xs text-bad">Low</span>}</td>
      <td className="px-2 text-center">{st?.stocked_qty ?? "-"}</td>
      <td className="px-2 text-center">{st?.sold_qty ?? "-"}</td>
      <td className="px-2 text-center">{st?.wasted_qty ?? "-"}</td>
      <td className="px-2 text-center font-semibold">{st?.available_qty ?? "-"}</td>
      <td className="px-2">
        <div className="flex items-center gap-2">
          <input className={num} inputMode="numeric" placeholder="Stock" aria-label={`Stock for ${p.name}`} value={qty} onChange={(e) => setQty(e.target.value)} />
          <input className={num} inputMode="numeric" placeholder="Min" aria-label={`Minimum for ${p.name}`} value={min} onChange={(e) => setMin(e.target.value)} />
          <Button variant="ghost" disabled={busy} onClick={save}>Save</Button>
        </div>
      </td>
      <td className="pl-2">
        <div className="flex items-center gap-2">
          <input className={num} inputMode="numeric" placeholder="Qty" aria-label={`Waste for ${p.name}`} value={waste} onChange={(e) => setWaste(e.target.value)} />
          <Button variant="ghost" disabled={busy || !st} onClick={logWaste}>Log</Button>
        </div>
      </td>
    </tr>
  );
}

export function Inventory() {
  const sess = useLoad(() => api.get<StallSession[]>("/stalls/sessions", { start: addDays(-7), end: addDays(14) }), []);
  const prods = useLoad(() => api.get<Product[]>("/products/admin/all"), []);
  const [sid, setSid] = useState("");
  const [low, setLow] = useState(false);
  const [msg, setMsg] = useState<Msg | null>(null);
  const list = sess.data ?? [];
  const chosen = sid || (list.find((s) => s.status === "open") ?? list.find((s) => s.session_date === isoDate()) ?? list[0])?.id || "";
  const stock = useLoad(
    () => (chosen ? api.get<StockAdmin[]>(`/inventory/sessions/${chosen}/admin`, low ? { low_stock_only: "true" } : undefined) : Promise.resolve([] as StockAdmin[])),
    [chosen, low],
  );
  const byProduct = new Map((stock.data ?? []).map((s) => [s.product_id, s]));
  const rows = (prods.data ?? []).filter((p) => p.is_active && (!low || byProduct.get(p.id)?.is_low_stock));
  const loading = (sess.loading && !sess.data) || (prods.loading && !prods.data);
  const error = sess.error || prods.error || stock.error;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Inventory</h1>
      <p className="text-sm text-muted">Stock is set per stall session. A product has no stock row until you save a quantity for it.</p>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      {loading && <PageSpinner />}
      {error && <Notice>{error}</Notice>}
      {sess.data && list.length === 0 && <Card className="text-center text-muted">No sessions from the last 7 days to the next 14. Create one under Stalls first.</Card>}

      {list.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-4">
            <select className={`${inp} w-auto`} value={chosen} onChange={(e) => setSid(e.target.value)} aria-label="Session">
              {list.map((s) => <option key={s.id} value={s.id}>{dayLabel(s.session_date)} · {s.location.name} · {s.status}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={low} onChange={(e) => setLow(e.target.checked)} /> Low stock only</label>
          </div>
          {stock.loading && !stock.data && <PageSpinner />}
          {rows.length === 0 && !loading && <Card className="text-center text-muted">{low ? "Nothing is low on stock." : "No products yet."}</Card>}
          {rows.length > 0 && (
            <Card className="overflow-x-auto p-4">
              <table className="w-full min-w-[44rem] text-left">
                <thead className="text-xs uppercase tracking-widest text-muted">
                  <tr><th className="pb-2">Product</th><th className="px-2 text-center">Stocked</th><th className="px-2 text-center">Sold</th><th className="px-2 text-center">Wasted</th><th className="px-2 text-center">Left</th><th className="px-2">Set stock / minimum</th><th className="pl-2">Waste</th></tr>
                </thead>
                <tbody>
                  {rows.map((p) => {
                    const st = byProduct.get(p.id);
                    return <Row key={`${p.id}-${st?.updated_at ?? "new"}`} p={p} st={st} sid={chosen}
                      done={(m) => { setMsg({ kind: "success", text: m }); stock.reload(); }} fail={(m) => setMsg({ kind: "error", text: m })} />;
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}