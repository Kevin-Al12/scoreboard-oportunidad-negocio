import { useEffect, useState } from "react";
import { Undo2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";

const ETIQUETAS_ENTIDAD = { sector: "Sector", criterio: "Criterio", evaluacion: "Evaluación" };

export default function AuditoriaPage() {
  const [entradas, setEntradas] = useState([]);
  const [entidad, setEntidad] = useState("");
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);

  function cargar() {
    setCargando(true);
    api
      .listarAuditoria(entidad ? { entidad } : {})
      .then(setEntradas)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }

  useEffect(cargar, [entidad]);

  async function revertir(id) {
    if (!confirm("¿Revertir este cambio al valor anterior?")) return;
    try {
      await api.revertirAuditoria(id);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Quién cambió qué, cuándo"
        title="Auditoría"
        pills={[
          { label: "Todo", active: entidad === "", onClick: () => setEntidad("") },
          { label: "Sectores", active: entidad === "sector", onClick: () => setEntidad("sector") },
          { label: "Criterios", active: entidad === "criterio", onClick: () => setEntidad("criterio") },
        ]}
      />

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ padding: 8 }}>
        {cargando ? (
          <p className="muted" style={{ padding: 18 }}>Cargando...</p>
        ) : entradas.length === 0 ? (
          <div className="empty-state">Todavía no hay cambios auditados. Edita un peso o un responsable para ver un registro aquí.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Entidad</th>
                <th>Campo</th>
                <th>De → A</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entradas.map((e) => (
                <tr key={e.id}>
                  <td className="muted">{new Date(e.creado_en).toLocaleString()}</td>
                  <td>{e.usuario_nombre}</td>
                  <td>{ETIQUETAS_ENTIDAD[e.entidad] || e.entidad} #{e.entidad_id}</td>
                  <td>{e.campo}</td>
                  <td>
                    <span className="muted">{e.valor_anterior ?? "—"}</span> → <strong>{e.valor_nuevo ?? "—"}</strong>
                  </td>
                  <td>
                    {e.revertido ? (
                      <span className="muted">Revertido</span>
                    ) : e.revertible ? (
                      <button className="btn secondary sm" onClick={() => revertir(e.id)}>
                        <Undo2 size={13} /> Revertir
                      </button>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
