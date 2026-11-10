import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { AdminOrder } from "../../api/adminModels";
import { StatusBadge } from "../../components/StatusBadge";
import { inp } from "../../components/inputs";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { dateTime, dayLabel, rupees } from "../../utils/format";

const STATUSES = ["pending", "confirmed", "preparing", "ready", "completed", "cancelled"];
const NEXT: Record<string, [string, string]> = {
  pending: ["confirmed", "Confirm"],
  confirmed: ["preparing", "Start preparing"],
  preparing: ["ready", "Mark ready"],
  ready: ["completed", "Complete"],
};

export function AdminOrders() {
  const [status, setStatus] = useState("");
  const { data, loading, error, reload } = useLoad(() => api.get<AdminOrder[]>("/orders", status ? { status, limit: 50 } : { limit: 50 }), [status]);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const t = setInterval(reload, 20000);
    return () => clearInterval(t);
  }, [reload]);

  async function move(o: AdminOrder, to: string) {
    if (to === "cancelled" && !window.confirm("Cancel this order?")) return;
    setBusy(o.id);
    setMsg("");
    try {
      await api.patch(`/orders/${o.id}/status`, { status: to });
      reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not update the order.");
    } finally {
      setBusy("");
    }
  }

  const orders = data ?? [];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Orders</h1>
        <select className={`${inp} w-auto`} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <p className="text-xs text-muted">Shows the latest 50 orders and refreshes every 20 seconds.</p>
      {msg && <Notice>{msg}</Notice>}
      {loading && !data && <PageSpinner />}
      {error && <div className="space-y-3"><Notice>{error}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>}
      {data && orders.length === 0 && <Card className="text-center text-muted">No orders {status ? `with status "${status}"` : "yet"}.</Card>}

      <ul className="space-y-4">
        {orders.map((o) => {
          const next = NEXT[o.status];
          return (
            <li key={o.id}>
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-bold">#{o.id.slice(0, 8)} · {o.customer_name}</p>
                    <a href={`tel:${o.customer_phone}`} className="text-sm text-terracotta">{o.customer_phone}</a>
                  </div>
                  <StatusBadge status={o.status} />
                </div>
                <p className="mt-2 text-sm">{o.items.map((i) => `${i.quantity} x ${i.product_name}`).join(", ")}</p>
                {o.notes && <p className="mt-1 text-sm text-muted">Note: {o.notes}</p>}
                <p className="mt-1 text-sm text-muted">{o.session.location.name} · {dayLabel(o.session.session_date)} · placed {dateTime(o.created_at)}</p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-lg font-bold">{rupees(o.total_amount)}</span>
                  <div className="flex gap-2">
                    {next && <Button disabled={busy === o.id} onClick={() => move(o, next[0])}>{next[1]}</Button>}
                    {next && <Button variant="ghost" disabled={busy === o.id} onClick={() => move(o, "cancelled")}>Cancel</Button>}
                  </div>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}