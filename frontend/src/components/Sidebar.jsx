import { NavLink } from "react-router-dom";
import { LayoutDashboard, Boxes, SlidersHorizontal, TrendingUp, History, KeyRound, Users, LogOut } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/sectores", label: "Sectores", icon: Boxes },
  { to: "/criterios", label: "Criterios", icon: SlidersHorizontal },
  { to: "/auditoria", label: "Auditoría", icon: History },
  { to: "/api-keys", label: "API keys", icon: KeyRound },
];

export default function Sidebar() {
  const { usuario, esAdmin, logout } = useAuth();

  const links = esAdmin ? [...LINKS, { to: "/equipo", label: "Equipo", icon: Users }] : LINKS;
  const iniciales = (usuario?.nombre_completo || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  return (
    <nav aria-label="Principal" className="rail">
      <div className="rail-mark">
        <TrendingUp size={19} strokeWidth={2.4} color="#ff9f6b" />
      </div>

      <div className="rail-nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            aria-label={label}
            title={label}
            className={({ isActive }) => `rail-btn${isActive ? " active" : ""}`}
          >
            <Icon size={18} strokeWidth={2} />
          </NavLink>
        ))}
      </div>

      <div className="rail-spacer" />

      {usuario && (
        <div className="rail-nav" style={{ gap: 10 }}>
          <div className="avatar" title={`${usuario.nombre_completo} · ${usuario.role}`}>
            {iniciales}
          </div>
          <button className="rail-btn" title="Cerrar sesión" aria-label="Cerrar sesión" onClick={logout}>
            <LogOut size={17} strokeWidth={2} />
          </button>
        </div>
      )}
    </nav>
  );
}
