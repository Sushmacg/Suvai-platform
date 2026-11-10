import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Order } from "../api/models";
import { SessionCard } from "../components/SessionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice, PageSpinner, btn } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { dateTime, rupees } from "../utils/format";

const STEPS = ["pending", "confirmed", "preparing", "ready", "completed"];
const CANCELLABLE = ["pending", "confirmed"];

export function OrderDetail() {
  const { id = "" } = useParams();
  const placed = (useLocation().state as { placed?: boolean } | null)?.placed;
  const { data: o, loading, error, reload } = useLoad(() => api.get<Order>(`/orders/me/${id}`), [id]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  // Refresh the status every 15 seconds while the order is still in progress.
  const live = !!o && STEPS.slice(0, 4).includes(o.status);
  useEffect(() => {
    if (!live) return;
    const t = setInterval(reload, 15000);
    return () => clearInterval(t);
  }, [live, reload]);

  async function cancel() {
    if (!window.confirm("Cancel this order?")) return;
    setBusy(true);
    setMsg("");
    try {
      await api.post(`/orders/me/${id}/cancel`);
      reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not cancel the order.");
    } finally {
      setBusy(false);
    }
  }

  if (loading && !o) return <PageSpinner />;
  if (error || !o) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-14">
        <Notice>{error || "Order not found."}</Notice>
        <Link to="/orders" className={btn("ghost")}>Back to my orders</Link>
      </div>
    );
  }
  const step = STEPS.indexOf(o.status);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link to="/orders" className="text-sm font-semibold text-terracotta">&larr; My orders</Link>
      {placed && <div className="mt-4"><Notice kind="success">Order placed! The stall will confirm it shortly.</Notice></div>}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold">Order #{o.id.slice(0, 8)}</h1>
        <StatusBadge status={o.status} />
      </div>
      <p className="text-sm text-muted">Placed {dateTime(o.created_at)}</p>

      {o.status === "cancelled" ? (
        <div className="mt-6"><Notice>This order was cancelled.</Notice></div>
      ) : (
        <ol className="mt-6 grid grid-cols-5 gap-1 text-center text-xs" aria-label="Order progress">
          {STEPS.map((s, i) => (
            <li key={s}>
              <div className={`mx-auto mb-1 h-2 rounded-full ${i <= step ? "bg-terracotta" : "bg-line"}`} />
              <span className={`capitalize ${i <= step ? "font-semibold text-terracotta-dark" : "text-muted"}`}>{s}</span>
            </li>
          ))}
        </ol>
      )}

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-xl font-bold">Items</h2>
          <ul className="divide-y divide-line">
            {o.items.map((i) => (
              <li key={i.product_id} className="flex justify-between py-2 text-sm">
                <span>{i.quantity} x {i.product_name} <span className="text-muted">({rupees(i.unit_price)})</span></span>
                <span className="font-semibold">{rupees(i.line_total)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex justify-between border-t border-line pt-3 text-lg font-bold"><span>Total</span><span>{rupees(o.total_amount)}</span></div>
          {o.notes && <p className="mt-3 text-sm text-muted">Note: {o.notes}</p>}
        </Card>
        <div>
          <h2 className="mb-3 text-xl font-bold">Pick up at</h2>
          <SessionCard s={o.session} />
        </div>
      </div>

      {msg && <div className="mt-4"><Notice>{msg}</Notice></div>}
      {CANCELLABLE.includes(o.status) && <div className="mt-6"><Button variant="ghost" disabled={busy} onClick={cancel}>{busy ? "Cancelling..." : "Cancel order"}</Button></div>}
    </div>
  );
}