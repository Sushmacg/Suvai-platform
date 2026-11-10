import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth, RequireRole } from "./components/Guards";
import { AdminLayout } from "./layouts/AdminLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { Home } from "./pages/Home";
import { CartProvider } from "./cart/CartContext";
import { Cart } from "./pages/Cart";
import { Menu } from "./pages/Menu";
import { ProductDetail } from "./pages/ProductDetail";
import { Stalls } from "./pages/Stalls";
import { Orders } from "./pages/Orders";
import { OrderDetail } from "./pages/OrderDetail";
import { Notifications } from "./pages/Notifications";
import { Dashboard } from "./pages/admin/Dashboard";
import { AdminProducts } from "./pages/admin/AdminProducts";
import { AdminOrders } from "./pages/admin/AdminOrders";
import { Inventory } from "./pages/admin/Inventory";
import { AdminStalls } from "./pages/admin/AdminStalls";
import { Expenses } from "./pages/admin/Expenses";
import { Forecast } from "./pages/admin/Forecast";
import { AdminReviews } from "./pages/admin/AdminReviews";
import { Assistant } from "./pages/admin/Assistant";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { NotFound, Soon } from "./pages/Soon";

const soon = (title: string) => <Soon title={title} />;

const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/menu", element: <Menu /> },
      { path: "/menu/:id", element: <ProductDetail /> },
      { path: "/stalls", element: <Stalls /> },
      { path: "/cart", element: <Cart /> },
      { path: "/login", element: <Login /> },
      { path: "/register", element: <Register /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "/orders", element: <Orders /> },
          { path: "/orders/:id", element: <OrderDetail /> },
          { path: "/notifications", element: <Notifications /> },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
  {
    path: "/admin",
    element: <RequireAuth />,
    children: [
      {
        element: <RequireRole role="admin" />,
        children: [
          {
            element: <AdminLayout />,
            children: [
              { index: true, element: <Dashboard /> },
              { path: "products", element: <AdminProducts /> },
              { path: "orders", element: <AdminOrders /> },
              { path: "inventory", element: <Inventory /> },
              { path: "stalls", element: <AdminStalls /> },
              { path: "expenses", element: <Expenses /> },
              { path: "forecast", element: <Forecast /> },
              { path: "reviews", element: <AdminReviews /> },
              { path: "assistant", element: <Assistant /> },
            ],
          },
        ],
      },
    ],
  },
]);

export default function App() {
  return (
    <AuthProvider>
      <CartProvider><RouterProvider router={router} /></CartProvider>
    </AuthProvider>
  );
}