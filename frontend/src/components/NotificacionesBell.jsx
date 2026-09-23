import { useEffect, useRef, useState } from "react";
import { Bell, Mail, MessageSquare, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

const ICONOS = { mencion: MessageSquare, umbral_oportunidad: TrendingUp };

export default function NotificacionesBell() {
  const [abierto, setAbierto] = useState(false);
  const [notifs, setNotifs] = useState([]);
  const ref = useRef(null);

  function cargar() {
    api.listarNotificaciones().then(setNotifs).catch(() => {});
  }

  useEffect(() => {
    cargar();
    const intervalo = setInterval(cargar, 30000);
    return () => clearInterval(intervalo);
  }, []);

  useEffect(() => {
    function onClickFuera(e) {
      if (ref.current && !ref.current.contains(e.target)) setAbierto(false);
    }
    document.addEventListener("mousedown", onClickFuera);
    return () => document.removeEventListener("mousedown", onClickFuera);
  }, []);

  const noLeidas = notifs.filter((n) => !n.leido).length;

  async function marcarLeida(id) {
    await api.marcarNotificacionLeida(id);
    cargar();
  }

  async function marcarTodas() {
    await api.marcarTodasLeidas();
    cargar();
  }

  return (
    <div style={{ position: "relative" }} ref={ref}>
      <button className="icon-btn" style={{ position: "relative" }} onClick={() => setAbierto((v) => !v)} aria-label="Notificaciones">
        <Bell size={18} />
        {noLeidas > 0 && (
          <span
            style={{
              position: "absolute",
              top: 6,
              right: 7,
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--alert)",
              border: "2px solid var(--surface)",
            }}
          />
        )}
      </button>

      {abierto && (
        <div
          className="card"
          style={{
            position: "absolute",
            right: 0,
            top: 50,
            width: 340,
            maxHeight: 420,
            overflowY: "auto",
            zIndex: 50,
            padding: 10,
          }}
        >
          <div className="row" style={{ justifyContent: "space-between", padding: "4px 6px 10px" }}>
            <strong style={{ fontSize: 14 }}>Notificaciones</strong>
            {noLeidas > 0 && (
              <button className="btn secondary sm" onClick={marcarTodas}>
                Marcar todas leídas
              </button>
            )}
          </div>
          {notifs.length === 0 && <div className="muted" style={{ padding: 10 }}>No tienes notificaciones.</div>}
          {notifs.map((n) => {
            const Icon = ICONOS[n.tipo] || Mail;
            const sectorId = n.entidad_ref?.startsWith("sector:") ? n.entidad_ref.split(":")[1] : null;
            return (
              <div
                key={n.id}
                onClick={() => !n.leido && marcarLeida(n.id)}
                style={{
                  display: "flex",
                  gap: 10,
                  padding: "10px 8px",
                  borderRadius: 12,
                  background: n.leido ? "transparent" : "var(--violet-100)",
                  cursor: n.leido ? "default" : "pointer",
                  marginBottom: 4,
                }}
              >
                <div className="avatar" style={{ background: "var(--surface-tint)" }}>
                  <Icon size={15} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: n.leido ? 500 : 700 }}>{n.mensaje}</div>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    {new Date(n.creado_en).toLocaleString()}
                    {sectorId && (
                      <>
                        {" · "}
                        <Link to={`/sectores/${sectorId}`} onClick={() => setAbierto(false)}>
                          ver sector
                        </Link>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
