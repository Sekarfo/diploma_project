import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";

export function AuthGuard(): JSX.Element {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}
