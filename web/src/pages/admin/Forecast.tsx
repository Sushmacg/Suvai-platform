import { useState } from "react";
import { api } from "../../api/client";
import type { ForecastResponse } from "../../api/adminModels";
import type { Location, Product } from "../../api/models";
import { inp, Label } from "../../components/inputs";
import { Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { addDays } from "../../utils/dates";
import { dayLabel } from "../../utils/format";

export function Forecast() {
  const [date, setDate] = useState(addDays(1));
  const [loc, setLoc] = useState("");
  const [prod, setProd] = useState("");
  const locs = useLoad(() => api.get<Location[]>("/stalls/locations/all"), []);
  const prods = useLoad(() => api.get<Product[]>("/products/admin/all"), []);
  const fc = useLoad(() => api.get<ForecastResponse>("/forecasts", { date, ...(loc ? { location_id: loc } : {}), ...(prod ? { product_id: prod } : {}) }), [date, loc, prod]);

  const lname = new Map((locs.data ?? []).map((l) => [l.id, l.name]));
  const pname = new Map((prods.data ?? []).map((p) => [p.id, p.name]));
  const groups = new Map<string, { product: string; units: number }[]>();
  for (const i of fc.data?.items ?? []) {
    const k = lname.get(i.location_id) ?? "Unknown location";
    groups.set(k, [...(groups.get(k) ?? []), { product: pname.get(i.product_id) ?? "Unknown product", units: i.predicted_units }]);
  }
  const max = Math.max(...(fc.data?.items ?? []).map((i) => i.predicted_units), 1);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Demand forecast</h1>
      <div className="flex flex-wrap items-end gap-3">
        <Label text="Date"><input type="date" className={`${inp} w-auto`} value={date} onChange={(e) => setDate(e.target.value)} /></Label>
        <Label text="Location"><select className={`${inp} w-auto`} value={loc} onChange={(e) => setLoc(e.target.value)}><option value="">All locations</option>{(locs.data ?? []).filter((l) => l.is_active).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></Label>
        <Label text="Product"><select className={`${inp} w-auto`} value={prod} onChange={(e) => setProd(e.target.value)}><option value="">All products</option>{(prods.data ?? []).filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Label>
      </div>

      {fc.loading && !fc.data && <PageSpinner />}
      {fc.error && <Notice>{fc.error}</Notice>}
      {fc.data && (
        <>
          <p className="text-sm text-muted">Forecast for {dayLabel(fc.data.forecast_date)} · model {fc.data.model_version}. These are model estimates of units sold, not guarantees.</p>
          {fc.data.items.length === 0 && <Card className="text-center text-muted">The model returned no predictions for this selection.</Card>}
          <div className="grid gap-6 md:grid-cols-2">
            {[...groups.entries()].map(([name, rows]) => (
              <Card key={name}>
                <div className="mb-3 flex items-baseline justify-between"><h2 className="text-xl font-bold">{name}</h2><span className="text-sm text-muted">about {Math.round(rows.reduce((n, r) => n + r.units, 0))} units</span></div>
                <ul className="space-y-3">
                  {rows.map((r) => (
                    <li key={r.product}>
                      <div className="flex justify-between text-sm"><span className="font-medium">{r.product}</span><span className="text-muted">{r.units.toFixed(1)}</span></div>
                      <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-saffron" style={{ width: `${(r.units / max) * 100}%` }} /></div>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}