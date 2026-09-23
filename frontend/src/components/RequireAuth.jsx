import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function RequireAuth({ children, soloAdmin = false }) {
  const { usuario, cargando, esAdmin } = useAuth();
  const location = useLocation();

  if (cargando) return null;
  if (!usuario) return <Navigate to="/login" state={{ from: location }} replace />;
  if (soloAdmin && !esAdmin) return <Navigate to="/dashboard" replace />;
  return children;
}
