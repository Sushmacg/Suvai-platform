import { useState } from "react";
import { api } from "../../api/client";
import type { LocationSales, SalesDay, Summary, TopProduct } from "../../api/adminModels";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { dayLabel, rupees } from "../../utils/format";

const DAYS = [7, 30, 90];

function Tile({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${tone}`}>{value}</p>
    </Card>
  );
}

function Bars({ rows, fmt }: { rows: { label: string; value: number; note?: string }[]; fmt: (n: number) => string }) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="flex justify-between gap-2 text-sm"><span className="font-medium">{r.label}</span><span className="text-muted">{r.note ? `${r.note} · ` : ""}{fmt(r.value)}</span></div>
          <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-terracotta" style={{ width: `${(r.value / max) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

export function Dashboard() {
  const [days, setDays] = useState(30);
  const sum = useLoad(() => api.get<Summary>("/analytics/summary", { days }), [days]);
  const sales = useLoad(() => api.get<SalesDay[]>("/analytics/sales", { days }), [days]);
  const prods = useLoad(() => api.get<TopProduct[]>("/analytics/products", { days, limit: 5 }), [days]);
  const locs = useLoad(() => api.get<LocationSales[]>("/analytics/locations", { days }), [days]);
  const s = sum.data;
  const err = sum.error || sales.error || prods.error || locs.error;
  const reload = () => { sum.reload(); sales.reload(); prods.reload(); locs.reload(); };
  const max = Math.max(...(sales.data ?? []).map((d) => d.revenue), 1);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          {s && <p className="text-sm text-muted">{dayLabel(s.from)} to {dayLabel(s.to)}</p>}
        </div>
        <div className="flex gap-2" role="group" aria-label="Period">
          {DAYS.map((d) => (
            <button key={d} onClick={() => setDays(d)} aria-pressed={days === d}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${days === d ? "bg-terracotta text-white" : "border border-line bg-white"}`}>{d} days</button>
          ))}
        </div>
      </div>

      {err && <div className="space-y-3"><Notice>{err}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>}
      {sum.loading && !s && <PageSpinner />}

      {s && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Tile label="Revenue" value={rupees(s.revenue)} />
            <Tile label="Orders" value={String(s.orders)} />
            <Tile label="Expenses" value={rupees(s.expenses)} />
            <Tile label="Profit" value={rupees(s.profit)} tone={s.profit >= 0 ? "text-ok" : "text-bad"} />
            <Tile label="Stocked" value={String(s.stocked)} />
            <Tile label="Sold" value={String(s.sold)} />
            <Tile label="Wasted" value={String(s.wasted)} />
            <Tile label="Sell-through" value={`${(s.sell_through * 100).toFixed(1)}%`} />
          </div>

          <Card>
            <h2 className="mb-4 text-xl font-bold">Revenue per day</h2>
            {(sales.data ?? []).length === 0 ? <p className="text-muted">No orders in this period.</p> : (
              <div className="flex h-48 gap-1.5" role="img" aria-label="Revenue per day">
                {(sales.data ?? []).map((d) => (
                  <div key={d.date} className="flex flex-1 flex-col" title={`${dayLabel(d.date)}: ${rupees(d.revenue)}, ${d.orders} orders`}>
                    <div className="flex flex-1 items-end"><div className="w-full rounded-t-md bg-saffron" style={{ height: `${Math.max(2, (d.revenue / max) * 100)}%` }} /></div>
                    <span className="mt-1 text-center text-[10px] text-muted">{d.date.slice(8)}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <h2 className="mb-4 text-xl font-bold">Top products</h2>
              {(prods.data ?? []).length === 0 ? <p className="text-muted">No sales yet.</p> :
                <Bars fmt={rupees} rows={(prods.data ?? []).map((p) => ({ label: p.name, value: p.revenue, note: `${p.units} sold` }))} />}
            </Card>
            <Card>
              <h2 className="mb-4 text-xl font-bold">Sales by location</h2>
              {(locs.data ?? []).length === 0 ? <p className="text-muted">No sales yet.</p> :
                <Bars fmt={rupees} rows={(locs.data ?? []).map((l) => ({ label: l.name, value: l.revenue, note: `${l.orders} orders` }))} />}
            </Card>
          </div>
          <p className="text-xs text-muted">All figures are computed by the backend from the orders, stock and expenses recorded in the database.</p>
        </>
      )}
    </div>
  );
}