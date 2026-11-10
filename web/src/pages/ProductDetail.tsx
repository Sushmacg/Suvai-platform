import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Product, PublicReview, RatingSummary } from "../api/models";
import { useAuth } from "../auth/AuthContext";
import { useCart } from "../cart/CartContext";
import { ProductImage } from "../components/ProductImage";
import { Stepper } from "../components/Stepper";
import { Button, Card, Notice, PageSpinner, btn } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { dateTime, rupees } from "../utils/format";

const Stars = ({ value }: { value: number }) => (
  <span aria-label={`${value} out of 5 stars`} className="text-saffron">{"★".repeat(Math.round(value))}{"☆".repeat(5 - Math.round(value))}</span>
);

function ReviewForm({ productId, onDone }: { productId: string; onDone: () => void }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api.post("/reviews", { product_id: productId, rating, comment: comment.trim() || null });
      setMsg({ kind: "success", text: "Thank you! Your review was posted." });
      setComment("");
      onDone();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof Error ? err.message : "Could not post the review." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div role="radiogroup" aria-label="Rating" className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} stars`} onClick={() => setRating(n)}
            className={`text-3xl transition ${n <= rating ? "text-saffron" : "text-line"}`}>★</button>
        ))}
      </div>
      <textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} rows={3} placeholder="Tell others what you liked (optional)"
        className="w-full rounded-xl border border-line bg-white px-3 py-2.5 outline-none focus:border-terracotta focus:ring-2 focus:ring-saffron/40" />
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      <Button type="submit" disabled={busy}>{busy ? "Posting..." : "Post review"}</Button>
    </form>
  );
}

export function ProductDetail() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const cart = useCart();
  const product = useLoad(() => api.get<Product>(`/products/${id}`, undefined, false), [id]);
  const summary = useLoad(() => api.get<RatingSummary>(`/reviews/product/${id}/summary`, undefined, false), [id]);
  const reviews = useLoad(() => api.get<PublicReview[]>(`/reviews/product/${id}`, { limit: 20 }, false), [id]);
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  if (product.loading && !product.data) return <PageSpinner />;
  if (product.error || !product.data) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-14">
        <Notice>{product.error || "Product not found."}</Notice>
        <Link to="/menu" className={btn("ghost")}>Back to the menu</Link>
      </div>
    );
  }
  const p = product.data;
  const s = summary.data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <Link to="/menu" className="text-sm font-semibold text-terracotta">&larr; Back to the menu</Link>
      <div className="mt-4 grid gap-8 md:grid-cols-2">
        <div className="overflow-hidden rounded-3xl bg-saffron-soft p-6">
          <ProductImage product={p} className="float mx-auto aspect-square w-full max-w-sm" />
        </div>
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">{p.category}</p>
          <h1 className="text-4xl font-bold">{p.name}</h1>
          {s && s.count > 0 && s.average !== null ? (
            <p className="flex items-center gap-2"><Stars value={s.average} /><span className="text-sm text-muted">{s.average.toFixed(1)} from {s.count} {s.count === 1 ? "review" : "reviews"}</span></p>
          ) : (
            <p className="text-sm text-muted">No reviews yet.</p>
          )}
          {p.description && <p className="text-lg text-muted">{p.description}</p>}
          <p className="text-3xl font-bold text-terracotta">{rupees(p.price)}</p>
          <div className="flex flex-wrap items-center gap-3">
            <Stepper value={qty} onChange={setQty} />
            <Button disabled={!p.is_available} onClick={() => { cart.add({ id: p.id, name: p.name, price: p.price }, qty); setAdded(true); setTimeout(() => setAdded(false), 1500); }}>
              {!p.is_available ? "Unavailable" : added ? "Added to cart" : "Add to cart"}
            </Button>
            <Link to="/cart" className={btn("ghost")}>Go to cart</Link>
          </div>
        </div>
      </div>

      <div className="mt-14 grid gap-8 md:grid-cols-3">
        <div className="md:col-span-1">
          <h2 className="text-2xl font-bold">Ratings</h2>
          {s && s.count > 0 ? (
            <ul className="mt-4 space-y-2">
              {[5, 4, 3, 2, 1].map((n) => {
                const c = s.stars[String(n)] ?? 0;
                return (
                  <li key={n} className="flex items-center gap-2 text-sm">
                    <span className="w-6">{n}★</span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-line"><span className="block h-full bg-saffron" style={{ width: `${(c / s.count) * 100}%` }} /></span>
                    <span className="w-6 text-right text-muted">{c}</span>
                  </li>
                );
              })}
            </ul>
          ) : <p className="mt-2 text-muted">Be the first to review this.</p>}
          <Card className="mt-6">
            <h3 className="mb-3 text-lg font-bold">Write a review</h3>
            {user ? (
              <>
                <p className="mb-3 text-xs text-muted">Only customers with a completed order for this product can review it.</p>
                <ReviewForm productId={p.id} onDone={() => { reviews.reload(); summary.reload(); }} />
              </>
            ) : (
              <Link to="/login" state={{ from: `/menu/${p.id}` }} className={btn()}>Log in to review</Link>
            )}
          </Card>
        </div>
        <div className="md:col-span-2">
          <h2 className="text-2xl font-bold">Reviews</h2>
          {reviews.error && <div className="mt-3"><Notice>{reviews.error}</Notice></div>}
          {reviews.data && reviews.data.length === 0 && <p className="mt-2 text-muted">No reviews yet.</p>}
          <ul className="mt-4 space-y-4">
            {(reviews.data ?? []).map((r) => (
              <li key={r.id}>
                <Card>
                  <div className="flex items-center justify-between"><span className="font-semibold">{r.reviewer_name}</span><Stars value={r.rating} /></div>
                  {r.comment && <p className="mt-2">{r.comment}</p>}
                  <p className="mt-2 text-xs text-muted">{dateTime(r.created_at)}</p>
                </Card>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}