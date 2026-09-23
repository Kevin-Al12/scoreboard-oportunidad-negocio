import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, FileSpreadsheet, Plus, Trash2, Upload, X } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { formatScore, textOnScore, violetForScore } from "../utils/score";
import { useAuth } from "../auth/AuthContext";

const SECTOR_VACIO = { nombre: "", descripcion: "", notas: "", fuentes_informacion: "" };
const POR_PAGINA = 10;

export default function SectoresPage() {
  const { usuario, puedeEditar } = useAuth();
  const [sectores, setSectores] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [soloMios, setSoloMios] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nuevo, setNuevo] = useState(SECTOR_VACIO);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [importando, setImportando] = useState(false);
  const navegar = useNavigate();
  const fileInputRef = useRef(null);

  function cargar() {
    setLoading(true);
    api
      .listarSectoresPaginado({
        limit: POR_PAGINA,
        offset: pagina * POR_PAGINA,
        responsable_id: soloMios ? usuario.id : undefined,
      })
      .then(({ items, total }) => {
        setSectores(items);
        setTotal(total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(cargar, [pagina, soloMios]); // eslint-disable-line react-hooks/exhaustive-deps

  async function crear(e) {
    e.preventDefault();
    try {
      await api.crearSector(nuevo);
      setNuevo(SECTOR_VACIO);
      setMostrarForm(false);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function eliminar(id, nombre) {
    if (!confirm(`¿Eliminar el sector "${nombre}"? Esto borra también su histórico de evaluaciones.`)) return;
    try {
      await api.eliminarSector(id);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function manejarImportacion(e) {
    const archivo = e.target.files?.[0];
    if (!archivo) return;
    setImportando(true);
    try {
      const resultado = await api.importarSectores(archivo);
      alert(`Importación completa: ${resultado.creados} creados, ${resultado.actualizados} actualizados.`);
      cargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setImportando(false);
      e.target.value = "";
    }
  }

  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  return (
    <div>
      <PageHeader
        eyebrow={`${total} sectores registrados`}
        title="Sectores / nichos"
        pills={[
          { label: "Todos", active: !soloMios, onClick: () => { setSoloMios(false); setPagina(0); } },
          { label: "Asignados a mí", active: soloMios, onClick: () => { setSoloMios(true); setPagina(0); } },
        ]}
        primaryAction={
          puedeEditar
            ? { label: mostrarForm ? "Cancelar" : "Nuevo sector", icon: mostrarForm ? X : Plus, onClick: () => setMostrarForm((v) => !v) }
            : undefined
        }
      />

      {error && <div className="error-banner">{error}</div>}

      {puedeEditar && (
        <div className="card" style={{ padding: 14 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div className="row">
              <button className="btn secondary sm" onClick={() => api.exportarSectoresCSV()}>
                <Download size={13} /> Exportar CSV
              </button>
              <button className="btn secondary sm" onClick={() => api.exportarSectoresExcel()}>
                <FileSpreadsheet size={13} /> Exportar Excel
              </button>
              <button className="btn secondary sm" onClick={() => fileInputRef.current?.click()} disabled={importando}>
                <Upload size={13} /> {importando ? "Importando..." : "Importar CSV/Excel"}
              </button>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" hidden onChange={manejarImportacion} />
            </div>
            <span className="muted">Columnas: nombre, descripcion, notas, fuentes_informacion, responsable_email</span>
          </div>
        </div>
      )}

      {mostrarForm && (
        <form className="card" onSubmit={crear} style={{ marginBottom: 4 }}>
          <div className="field">
            <label>Nombre</label>
            <input
              required
              value={nuevo.nombre}
              onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })}
              placeholder="Ej. Lavado de autos a domicilio"
              style={{ width: "100%" }}
            />
          </div>
          <div className="field">
            <label>Descripción</label>
            <textarea
              rows={2}
              value={nuevo.descripcion}
              onChange={(e) => setNuevo({ ...nuevo, descripcion: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Notas (por qué destaca / observaciones)</label>
            <textarea
              rows={2}
              value={nuevo.notas}
              onChange={(e) => setNuevo({ ...nuevo, notas: e.target.value })}
            />
          </div>
          <div className="field" style={{ marginBottom: 18 }}>
            <label>Fuentes de información</label>
            <input
              value={nuevo.fuentes_informacion}
              onChange={(e) => setNuevo({ ...nuevo, fuentes_informacion: e.target.value })}
              placeholder="Ej. observación de mercado, entrevistas, reportes ONE"
              style={{ width: "100%" }}
            />
          </div>
          <button className="btn" type="submit">
            Guardar sector
          </button>
        </form>
      )}

      <div className="card" style={{ padding: 8 }}>
        {loading ? (
          <p style={{ padding: 18 }} className="muted">
            Cargando...
          </p>
        ) : sectores.length === 0 ? (
          <div className="empty-state">
            {soloMios ? (
              "No tienes sectores asignados."
            ) : (
              <>
                No hay sectores todavía. Crea el primero, o corre <code>python seed.py</code> en el backend
                para cargar 8 sectores de ejemplo.
              </>
            )}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Sector</th>
                <th>Responsable</th>
                <th>Score actual</th>
                <th>Última evaluación</th>
                {puedeEditar && <th></th>}
              </tr>
            </thead>
            <tbody>
              {sectores.map((s) => (
                <tr key={s.id} className="clickable" onClick={() => navegar(`/sectores/${s.id}`)}>
                  <td>
                    <div style={{ fontWeight: 700 }}>{s.nombre}</div>
                    <div className="muted">{s.descripcion}</div>
                  </td>
                  <td className="muted">{s.responsable_nombre || "—"}</td>
                  <td>
                    <span
                      className="score-chip"
                      style={{ background: violetForScore(s.score_0_a_100), color: textOnScore(s.score_0_a_100) }}
                    >
                      {s.score_0_a_100 === null ? "Sin evaluar" : `${formatScore(s.score_0_a_100)} / 100`}
                    </span>
                  </td>
                  <td className="muted">
                    {s.fecha_ultima_evaluacion ? new Date(s.fecha_ultima_evaluacion).toLocaleDateString() : "—"}
                  </td>
                  {puedeEditar && (
                    <td>
                      <button
                        className="icon-btn"
                        style={{ width: 38, height: 38 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          eliminar(s.id, s.nombre);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPaginas > 1 && (
        <div className="row" style={{ justifyContent: "center" }}>
          <button className="btn secondary sm" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>
            ← Anterior
          </button>
          <span className="muted">
            Página {pagina + 1} de {totalPaginas}
          </span>
          <button className="btn secondary sm" disabled={pagina >= totalPaginas - 1} onClick={() => setPagina((p) => p + 1)}>
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
