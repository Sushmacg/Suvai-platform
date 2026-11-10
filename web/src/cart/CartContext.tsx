import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Line = { productId: string; name: string; price: string; qty: number };
type Item = { id: string; name: string; price: string };
type Cart = {
  lines: Line[];
  count: number;
  total: number;
  add: (p: Item, qty?: number) => void;
  setQty: (id: string, qty: number) => void;
  remove: (id: string) => void;
  clear: () => void;
};

const KEY = "suvai.cart";
const load = (): Line[] => {
  try { const r = localStorage.getItem(KEY); return r ? (JSON.parse(r) as Line[]) : []; } catch { return []; }
};
const Ctx = createContext<Cart | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<Line[]>(load);
  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(lines)); } catch { /* storage unavailable */ }
  }, [lines]);

  const add = useCallback((p: Item, qty = 1) => setLines((cur) => {
    const found = cur.find((l) => l.productId === p.id);
    if (found) return cur.map((l) => (l.productId === p.id ? { ...l, qty: Math.min(50, l.qty + qty) } : l));
    return [...cur, { productId: p.id, name: p.name, price: p.price, qty: Math.min(50, qty) }];
  }), []);
  const setQty = useCallback((id: string, qty: number) => setLines((cur) => cur.map((l) => (l.productId === id ? { ...l, qty: Math.max(1, Math.min(50, qty)) } : l))), []);
  const remove = useCallback((id: string) => setLines((cur) => cur.filter((l) => l.productId !== id)), []);
  const clear = useCallback(() => setLines([]), []);

  const value = useMemo(() => ({
    lines,
    count: lines.reduce((n, l) => n + l.qty, 0),
    total: lines.reduce((n, l) => n + Number(l.price) * l.qty, 0),
    add, setQty, remove, clear,
  }), [lines, add, setQty, remove, clear]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCart(): Cart {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCart must be used inside CartProvider");
  return v;
}