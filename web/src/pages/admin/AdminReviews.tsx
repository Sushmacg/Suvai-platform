import { useState } from "react";
import { api } from "../../api/client";
import type { AdminReview } from "../../api/adminModels";
import { inp, Label } from "../../components/inputs";
import { Button, Card, Notice, PageSpinner } from "../../components/ui";
import { useLoad } from "../../hooks/useLoad";
import { dateTime } from "../../utils/format";

export function AdminReviews() {
  const [vis, setVis] = useState("");
  const [rating, setRating] = useState("");
  const q = { limit: 50, ...(vis ? { hidden: vis } : {}), ...(rating ? { rating } : {}) };
  const { data, loading, error, reload } = useLoad(() => api.get<AdminReview[]>("/reviews/admin", q), [vis, rating]);
  const [hiding, setHiding] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  async function act(id: string, path: string, body: object | undefined, ok: string) {
    setBusy(id);
    setMsg(null);
    try { await api.post(`/reviews/admin/${id}/${path}`, body); setHiding(""); setReason(""); setMsg({ kind: "success", text: ok }); reload(); }
    catch (e) { setMsg({ kind: "error", text: e instanceof Error ? e.message : "Request failed." }); }
    finally { setBusy(""); }
  }

  const items = data ?? [];
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Reviews</h1>
      <div className="flex flex-wrap items-end gap-3">
        <Label text="Visibility"><select className={`${inp} w-auto`} value={vis} onChange={(e) => setVis(e.target.value)}><option value="">All</option><option value="false">Visible</option><option value="true">Hidden</option></select></Label>
        <Label text="Rating"><select className={`${inp} w-auto`} value={rating} onChange={(e) => setRating(e.target.value)}><option value="">Any</option>{[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} stars</option>)}</select></Label>
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      {loading && !data && <PageSpinner />}
      {error && <Notice>{error}</Notice>}
      {data && items.length === 0 && <Card className="text-center text-muted">No reviews match this view.</Card>}

      <ul className="space-y-4">
        {items.map((r) => (
          <li key={r.id}>
            <Card className={r.is_hidden ? "opacity-70" : ""}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-bold">{r.product_name} <span className="text-saffron" aria-label={`${r.rating} stars`}>{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</span></p>
                {r.is_hidden && <span className="rounded-full bg-line px-3 py-1 text-xs font-semibold text-muted">Hidden</span>}
              </div>
              {r.comment ? <p className="mt-2">{r.comment}</p> : <p className="mt-2 text-sm text-muted">No comment.</p>}
              <p className="mt-2 text-xs text-muted">{r.customer_name} · {r.customer_phone} · {dateTime(r.created_at)}</p>
              {r.is_hidden && r.hidden_reason && <p className="mt-1 text-xs text-muted">Reason: {r.hidden_reason}</p>}
              <div className="mt-3">
                {r.is_hidden ? (
                  <Button variant="ghost" disabled={busy === r.id} onClick={() => act(r.id, "restore", undefined, "Review restored.")}>Restore</Button>
                ) : hiding === r.id ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <input className={`${inp} max-w-xs`} placeholder="Reason (optional)" maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} />
                    <Button disabled={busy === r.id} onClick={() => act(r.id, "hide", { reason: reason.trim() || null }, "Review hidden.")}>Confirm hide</Button>
                    <Button variant="ghost" onClick={() => setHiding("")}>Cancel</Button>
                  </div>
                ) : (
                  <Button variant="ghost" onClick={() => { setHiding(r.id); setReason(""); }}>Hide</Button>
                )}
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {items.length === 50 && <p className="text-xs text-muted">Showing the latest 50. Use the filters to narrow down.</p>}
    </div>
  );
}