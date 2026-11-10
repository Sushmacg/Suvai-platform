import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { PageSpinner } from "./ui";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <PageSpinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <Outlet />;
}

export function RequireRole({ role }: { role: string }) {
  const { user } = useAuth();
  if (user?.role !== role) return <Navigate to="/" replace />;
  return <Outlet />;
}