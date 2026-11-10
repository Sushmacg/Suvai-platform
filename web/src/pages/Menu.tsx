import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Product } from "../api/models";
import { useCart } from "../cart/CartContext";
import { ProductImage } from "../components/ProductImage";
import { Button, Card, Notice, PageSpinner, btn } from "../components/ui";
import { useLoad } from "../hooks/useLoad";
import { rupees } from "../utils/format";

export function Menu() {
  const { data, loading, error, reload } = useLoad(() => api.get<Product[]>("/products", undefined, false), []);
  const cart = useCart();
  const [cat, setCat] = useState("All");
  const [added, setAdded] = useState("");
  const items = data ?? [];
  const cats = ["All", ...new Set(items.map((p) => p.category))];
  const shown = cat === "All" ? items : items.filter((p) => p.category === cat);

  function add(p: Product) {
    cart.add({ id: p.id, name: p.name, price: p.price });
    setAdded(p.id);
    setTimeout(() => setAdded(""), 1200);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-4xl font-bold">Our menu</h1>
      <p className="mt-1 text-muted">Heart-shaped nankhatai, baked fresh. Order ahead and collect at the stall.</p>

      {loading && !data && <PageSpinner />}
      {error && (
        <div className="mt-6 space-y-3"><Notice>{error}</Notice><Button variant="ghost" onClick={reload}>Try again</Button></div>
      )}
      {data && cats.length > 2 && (
        <div className="mt-6 flex flex-wrap gap-2" aria-label="Categories">
          {cats.map((c) => (
            <button key={c} onClick={() => setCat(c)} aria-pressed={cat === c}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${cat === c ? "bg-terracotta text-white" : "border border-line bg-white hover:bg-saffron-soft"}`}>{c}</button>
          ))}
        </div>
      )}
      {data && shown.length === 0 && <Card className="mt-8 text-center text-muted">No products to show right now.</Card>}

      <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((p) => (
          <Card key={p.id} className="flex flex-col overflow-hidden p-0 transition hover:-translate-y-1 hover:shadow-md">
            <Link to={`/menu/${p.id}`} className="block bg-saffron-soft" aria-label={`View ${p.name}`}>
              <ProductImage product={p} className="mx-auto aspect-square w-full max-w-[16rem] p-4" />
            </Link>
            <div className="flex flex-1 flex-col gap-2 p-5">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted">{p.category}</p>
              <h2 className="text-xl font-bold">{p.name}</h2>
              {p.description && <p className="line-clamp-2 text-sm text-muted">{p.description}</p>}
              <p className="mt-auto text-lg font-bold text-terracotta">{rupees(p.price)}</p>
              <div className="flex gap-2">
                <Link to={`/menu/${p.id}`} className={btn("ghost", "flex-1")}>Details</Link>
                <Button className="flex-1" disabled={!p.is_available} onClick={() => add(p)}>
                  {!p.is_available ? "Unavailable" : added === p.id ? "Added" : "Add to cart"}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}