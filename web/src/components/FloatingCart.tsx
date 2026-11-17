import { Link } from "react-router-dom";
import { useCart } from "../cart/CartContext";
import { rupees } from "../utils/format";

// Stays on screen while the customer scrolls the menu, so checkout is one tap away.
export function FloatingCart() {
  const { count, total } = useCart();
  if (count === 0) return null;
  return (
    <Link to="/cart" aria-label={`Open cart, ${count} items`}
      className="fixed bottom-5 right-5 z-30 rounded-full bg-terracotta px-5 py-3 font-semibold text-white shadow-lg transition hover:bg-terracotta-dark">
      Cart · {count} · {rupees(total)}
    </Link>
  );
}