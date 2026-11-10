import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Order } from "../api/models";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice, PageSpinner, btn } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { dateTime, dayLabel, rupees } from "../utils/format";

const ACTIVE = ["pending", "confirmed", "preparing", "ready"];
const FILTERS = ["All", "Active", "Past"] as const;

export function Orders() {
  const { data, loading, error, reload } = useLoad(() => api.get<Order[]>("/orders/me", { limit: 50 }), []);
  const [f, setF] = useState<(typeof FILTERS)[number]>("All");
  const all = data ?? [];
  const shown = all.filter((o) => f === "All" || (f === "Active") === ACTIVE.includes(o.status));

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-4xl font-bold">My orders</h1>
        <div className="flex gap-2">
          {FILTERS.map((x) => (
            <button key={x} onClick={() => setF(x)} aria-pressed={f === x}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${f === x ? "bg-terracotta text-white" : "border border-line bg-white"}`}>{x}</button>
          ))}
        </div>
      </div>

      {loading && !data && <PageSpinner />}
      {error && <div className="mt-6 space-y-3"><Notice>{error}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>}
      {data && shown.length === 0 && (
        <Card className="mt-8 text-center">
          <p className="text-muted">{all.length === 0 ? "You have not placed any orders yet." : "No orders in this view."}</p>
          {all.length === 0 && <Link to="/menu" className={btn("primary", "mt-4")}>View the menu</Link>}
        </Card>
      )}

      <ul className="mt-6 space-y-4">
        {shown.map((o) => (
          <li key={o.id}>
            <Link to={`/orders/${o.id}`} className="block">
              <Card className="transition hover:-translate-y-0.5 hover:shadow-md">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold">{o.session.location.name} · {dayLabel(o.session.session_date)}</span>
                  <StatusBadge status={o.status} />
                </div>
                <p className="mt-1 text-sm text-muted">{o.items.map((i) => `${i.quantity} x ${i.product_name}`).join(", ")}</p>
                <div className="mt-2 flex justify-between text-sm"><span className="text-muted">{dateTime(o.created_at)}</span><span className="font-bold">{rupees(o.total_amount)}</span></div>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}