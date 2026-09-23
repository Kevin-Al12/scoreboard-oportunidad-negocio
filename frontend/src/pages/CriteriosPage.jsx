import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../auth/AuthContext";

const CRITERIO_VACIO = { nombre: "", peso: 10, descripcion: "" };
const SERIES = ["#3a24b8", "#4a30dc", "#5b3df5", "#7f66f8", "#9a86fa", "#b6a8fb"];

export default function CriteriosPage() {
  const { puedeEditar, esAdmin } = useAuth();
  const [criterios, setCriterios] = useState([]);
  const [error, setError] = useState(null);
  const [nuevo, setNuevo] = useState(CRITERIO_VACIO);
  const [editando, setEditando] = useState({});

  function cargar() {
    api.listarCriterios().then(setCriterios).catch((e) => setError(e.message));
  }

  useEffect(cargar, []);

  const activos = criterios.filter((c) => c.activo);
  const pesoTotal = activos.reduce((acc, c) => acc + c.peso, 0);

  async function crear(e) {
    e.preventDefault();
    try {
      await api.crearCriterio({ ...nuevo, peso: Number(nuevo.peso) });
      setNuevo(CRITERIO_VACIO);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function guardarPeso(id) {
    const nuevoPeso = Number(editando[id]);
    if (!nuevoPeso || nuevoPeso <= 0) return;
    try {
      await api.actualizarCriterio(id, { peso: nuevoPeso });
      setEditando((prev) => {
        const copia = { ...prev };
        delete copia[id];
        return copia;
      });
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggleActivo(c) {
    try {
      await api.actualizarCriterio(c.id, { activo: !c.activo });
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function eliminar(c) {
    if (!confirm(`¿Eliminar el criterio "${c.nombre}"? Esto afecta el score de todos los sectores.`)) return;
    try {
      await api.eliminarCriterio(c.id);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Los pesos se normalizan automáticamente" title="Criterios de evaluación" />

      {error && <div className="error-banner">{error}</div>}

      <div className="card tint" style={{ marginBottom: 20 }}>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-muted)", fontWeight: 600 }}>
          Los pesos no necesitan sumar exactamente 100%: el motor de scoring los normaliza
          automáticamente entre los criterios activos antes de calcular.
        </p>
      </div>

      <div className="card" style={{ padding: 8 }}>
        <table>
          <thead>
            <tr>
              <th>Criterio</th>
              <th style={{ width: 150 }}>Peso</th>
              <th style={{ width: 220 }}>% normalizado</th>
              <th style={{ width: 70 }}>Activo</th>
              {esAdmin && <th></th>}
            </tr>
          </thead>
          <tbody>
            {criterios.map((c) => {
              const idx = activos.findIndex((a) => a.id === c.id);
              const pct = c.activo && pesoTotal > 0 ? (c.peso / pesoTotal) * 100 : 0;
              const color = c.activo ? SERIES[idx % SERIES.length] : "#c7c1e8";
              return (
                <tr key={c.id} style={{ opacity: c.activo ? 1 : 0.5 }}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ width: 10, height: 10, borderRadius: 3, background: color, flexShrink: 0 }} />
                      <div>
                        <div style={{ fontWeight: 700 }}>{c.nombre}</div>
                        <div className="muted">{c.descripcion}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        style={{ width: 74 }}
                        disabled={!puedeEditar}
                        value={editando[c.id] ?? c.peso}
                        onChange={(e) => setEditando({ ...editando, [c.id]: e.target.value })}
                      />
                      {puedeEditar && editando[c.id] !== undefined && editando[c.id] != String(c.peso) && (
                        <button className="btn secondary sm" onClick={() => guardarPeso(c.id)}>
                          OK
                        </button>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="row" style={{ gap: 8, flexWrap: "nowrap" }}>
                      <div className="bar-track" style={{ flex: 1, minWidth: 80 }}>
                        <div style={{ width: `${pct}%`, height: "100%", borderRadius: 999, background: color }} />
                      </div>
                      <span className="muted" style={{ width: 42, textAlign: "right" }}>
                        {c.activo ? `${pct.toFixed(0)}%` : "—"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <input type="checkbox" checked={c.activo} disabled={!puedeEditar} onChange={() => toggleActivo(c)} />
                  </td>
                  {esAdmin && (
                    <td>
                      <button className="icon-btn" style={{ width: 38, height: 38 }} onClick={() => eliminar(c)}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {puedeEditar && (
      <div className="card" style={{ marginTop: 20 }}>
        <h3 style={{ marginBottom: 16 }}>Nuevo criterio</h3>
        <form onSubmit={crear} className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 2, minWidth: 200, marginBottom: 0 }}>
            <label>Nombre</label>
            <input
              required
              value={nuevo.nombre}
              onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })}
              style={{ width: "100%" }}
            />
          </div>
          <div className="field" style={{ width: 100, marginBottom: 0 }}>
            <label>Peso</label>
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={nuevo.peso}
              onChange={(e) => setNuevo({ ...nuevo, peso: e.target.value })}
            />
          </div>
          <div className="field" style={{ flex: 3, minWidth: 220, marginBottom: 0 }}>
            <label>Descripción / convención de escala</label>
            <input
              value={nuevo.descripcion}
              onChange={(e) => setNuevo({ ...nuevo, descripcion: e.target.value })}
              placeholder="Ej. 5 = favorable a la oportunidad"
              style={{ width: "100%" }}
            />
          </div>
          <button className="btn" type="submit">
            <Plus size={15} /> Agregar
          </button>
        </form>
      </div>
      )}
    </div>
  );
}
