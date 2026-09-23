import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowLeft, ClipboardList, History, MessageSquare, Send, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { formatScore, textOnScore, violetForScore } from "../utils/score";
import { useAuth } from "../auth/AuthContext";

export default function SectorDetallePage() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { usuario, puedeEditar } = useAuth();

  const [sector, setSector] = useState(null);
  const [criterios, setCriterios] = useState([]);
  const [rondas, setRondas] = useState([]);
  const [radar, setRadar] = useState(null);
  const [historico, setHistorico] = useState(null);
  const [usuariosOrg, setUsuariosOrg] = useState([]);
  const [comentarios, setComentarios] = useState([]);
  const [error, setError] = useState(null);

  const [calificaciones, setCalificaciones] = useState({});
  const [notasRonda, setNotasRonda] = useState("");
  const [guardandoRonda, setGuardandoRonda] = useState(false);
  const [nuevoComentario, setNuevoComentario] = useState("");

  function cargarTodo() {
    api.obtenerSector(id).then(setSector).catch((e) => setError(e.message));
    api.listarRondas(id).then(setRondas).catch(() => {});
    api
      .radarDeSector(id)
      .then(setRadar)
      .catch(() => setRadar(null));
    api
      .historicoDeSector(id)
      .then(setHistorico)
      .catch(() => setHistorico(null));
    api.listarComentarios(id).then(setComentarios).catch(() => {});
  }

  useEffect(() => {
    api.listarCriterios({ solo_activos: true }).then(setCriterios).catch((e) => setError(e.message));
    api.listarUsuarios().then(setUsuariosOrg).catch(() => {});
    cargarTodo();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function guardarCampoSector(campo, valor) {
    try {
      await api.actualizarSector(id, { [campo]: valor });
    } catch (e) {
      setError(e.message);
    }
  }

  async function cambiarResponsable(responsableId) {
    try {
      const actualizado = await api.actualizarSector(id, { responsable_id: responsableId || null });
      setSector((prev) => ({ ...prev, responsable_id: actualizado.responsable_id }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function registrarRonda(e) {
    e.preventDefault();
    const criteriosActivos = criterios.filter((c) => c.activo);
    const faltantes = criteriosActivos.filter((c) => !calificaciones[c.id]);
    if (faltantes.length > 0) {
      setError(`Falta calificar: ${faltantes.map((c) => c.nombre).join(", ")}`);
      return;
    }
    setGuardandoRonda(true);
    try {
      await api.crearRonda(id, {
        notas: notasRonda,
        calificaciones: criteriosActivos.map((c) => ({
          criterio_id: c.id,
          calificacion: Number(calificaciones[c.id]),
        })),
      });
      setCalificaciones({});
      setNotasRonda("");
      cargarTodo();
    } catch (e) {
      setError(e.message);
    } finally {
      setGuardandoRonda(false);
    }
  }

  async function borrarRonda(rondaId) {
    if (!confirm("¿Eliminar esta evaluación del histórico?")) return;
    try {
      await api.eliminarRonda(id, rondaId);
      cargarTodo();
    } catch (e) {
      setError(e.message);
    }
  }

  async function enviarComentario(e) {
    e.preventDefault();
    if (!nuevoComentario.trim()) return;
    try {
      await api.crearComentario(id, nuevoComentario);
      setNuevoComentario("");
      api.listarComentarios(id).then(setComentarios);
    } catch (e) {
      setError(e.message);
    }
  }

  async function borrarComentario(comentarioId) {
    try {
      await api.eliminarComentario(id, comentarioId);
      setComentarios((prev) => prev.filter((c) => c.id !== comentarioId));
    } catch (e) {
      setError(e.message);
    }
  }

  if (!sector) return <p className="muted" style={{ padding: 20 }}>Cargando...</p>;

  const datosRadar = radar?.detalle.map((d) => ({ criterio: d.criterio_nombre, valor: d.valor, fullMark: 5 })) || [];
  const datosHistorico =
    historico?.puntos.map((p) => ({ fecha: p.fecha, score: p.score_0_a_100 })) || [];

  return (
    <div>
      <button className="btn secondary sm" onClick={() => navegar("/sectores")} style={{ marginBottom: 6 }}>
        <ArrowLeft size={14} /> Volver a sectores
      </button>

      {error && <div className="error-banner">{error}</div>}

      <div className="ph" style={{ alignItems: "flex-start" }}>
        <div className="ph-titles">
          <div className="ph-eyebrow">Sector / nicho</div>
          <h1 className="ph-title">{sector.nombre}</h1>
          <p className="muted" style={{ margin: "2px 0 0" }}>{sector.descripcion}</p>
        </div>
        <span
          className="score-chip"
          style={{ background: violetForScore(sector.score_0_a_100), color: textOnScore(sector.score_0_a_100), fontSize: 15 }}
        >
          {sector.score_0_a_100 === null ? "Sin evaluar" : `${formatScore(sector.score_0_a_100)} / 100`}
        </span>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Información del sector</h3>
          <div className="field">
            <label>Responsable asignado</label>
            <select
              value={sector.responsable_id || ""}
              onChange={(e) => cambiarResponsable(e.target.value ? Number(e.target.value) : null)}
              disabled={!puedeEditar}
              style={{ width: "100%" }}
            >
              <option value="">Sin asignar</option>
              {usuariosOrg.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombre_completo}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Descripción</label>
            <textarea
              rows={2}
              defaultValue={sector.descripcion}
              disabled={!puedeEditar}
              onBlur={(e) => guardarCampoSector("descripcion", e.target.value)}
            />
          </div>
          <div className="field">
            <label>Notas</label>
            <textarea
              rows={3}
              defaultValue={sector.notas}
              disabled={!puedeEditar}
              onBlur={(e) => guardarCampoSector("notas", e.target.value)}
            />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Fuentes de información</label>
            <textarea
              rows={2}
              defaultValue={sector.fuentes_informacion}
              disabled={!puedeEditar}
              onBlur={(e) => guardarCampoSector("fuentes_informacion", e.target.value)}
            />
          </div>
          {puedeEditar && <p className="muted" style={{ marginTop: 10 }}>Los cambios se guardan al salir del campo.</p>}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Radar — última evaluación</h3>
          {datosRadar.length === 0 ? (
            <div className="empty-state">Este sector todavía no tiene evaluaciones.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={datosRadar}>
                <PolarGrid stroke="#e5e0fa" />
                <PolarAngleAxis dataKey="criterio" tick={{ fontSize: 11, fill: "#5e5885" }} />
                <Radar dataKey="valor" stroke="#5b3df5" fill="#5b3df5" fillOpacity={0.28} strokeWidth={2} />
                <Tooltip formatter={(v) => [`${v} / 5`, "Calificación"]} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {datosHistorico.length > 1 && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Evolución del score en el tiempo</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={datosHistorico} margin={{ left: -10, right: 20 }}>
              <XAxis dataKey="fecha" tick={{ fontSize: 11, fill: "#8a8296" }} axisLine={{ stroke: "#e5e0fa" }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#8a8296" }} axisLine={{ stroke: "#e5e0fa" }} tickLine={false} />
              <Tooltip formatter={(v) => [`${v.toFixed(1)} / 100`, "Score"]} />
              <Line type="monotone" dataKey="score" stroke="#5b3df5" strokeWidth={2.5} dot={{ r: 4, fill: "#5b3df5" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {puedeEditar && (
        <div className="card">
          <h3 style={{ marginBottom: 4 }}>
            <ClipboardList size={16} style={{ marginRight: 7, verticalAlign: -3 }} />
            Registrar nueva evaluación
          </h3>
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            Crea una ronda de evaluación nueva con la fecha de hoy. La anterior se conserva en el histórico.
          </p>
          <form onSubmit={registrarRonda}>
            {criterios
              .filter((c) => c.activo)
              .map((c) => (
                <div key={c.id} className="field">
                  <label>
                    {c.nombre} <span className="muted" style={{ fontWeight: 400 }}>({c.descripcion})</span>
                  </label>
                  <select
                    value={calificaciones[c.id] || ""}
                    onChange={(e) => setCalificaciones({ ...calificaciones, [c.id]: e.target.value })}
                  >
                    <option value="">Calificar (1-5)</option>
                    {[1, 2, 3, 4, 5].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            <div className="field">
              <label>Notas de esta evaluación</label>
              <textarea rows={2} value={notasRonda} onChange={(e) => setNotasRonda(e.target.value)} />
            </div>
            <button className="btn" type="submit" disabled={guardandoRonda}>
              {guardandoRonda ? "Guardando..." : "Guardar evaluación"}
            </button>
          </form>
        </div>
      )}

      <div className="card" style={{ padding: 8 }}>
        <h3 style={{ margin: "14px 16px 10px" }}>
          <History size={16} style={{ marginRight: 7, verticalAlign: -3 }} />
          Histórico de evaluaciones
        </h3>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Score</th>
              <th>Notas</th>
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {rondas.map((r) => {
              const score = historico?.puntos.find((p) => p.ronda_id === r.id)?.score_0_a_100 ?? null;
              return (
                <tr key={r.id}>
                  <td>{r.fecha}</td>
                  <td>
                    <span className="score-chip" style={{ background: violetForScore(score), color: textOnScore(score), fontSize: 12.5 }}>
                      {score !== null ? score.toFixed(1) : "—"}
                    </span>
                  </td>
                  <td className="muted">{r.notas}</td>
                  {puedeEditar && (
                    <td>
                      <button className="icon-btn" style={{ width: 36, height: 36 }} onClick={() => borrarRonda(r.id)}>
                        <Trash2 size={13} />
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 14 }}>
          <MessageSquare size={16} style={{ marginRight: 7, verticalAlign: -3 }} />
          Comentarios
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
          {comentarios.length === 0 && <p className="muted">Sin comentarios todavía.</p>}
          {comentarios.map((c) => (
            <div key={c.id} style={{ display: "flex", gap: 10 }}>
              <div className="avatar">
                {c.autor_nombre
                  .split(" ")
                  .slice(0, 2)
                  .map((w) => w[0])
                  .join("")
                  .toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong style={{ fontSize: 13.5 }}>{c.autor_nombre}</strong>
                  <span className="muted" style={{ fontSize: 11 }}>{new Date(c.creado_en).toLocaleString()}</span>
                </div>
                <p style={{ margin: "2px 0 0", fontSize: 14 }}>{c.texto}</p>
              </div>
              {(c.user_id === usuario.id || usuario.role === "admin") && (
                <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => borrarComentario(c.id)}>
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          ))}
        </div>
        <form onSubmit={enviarComentario} className="row" style={{ flexWrap: "nowrap" }}>
          <input
            placeholder="Escribe un comentario — usa @nombre para mencionar a alguien del equipo"
            value={nuevoComentario}
            onChange={(e) => setNuevoComentario(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn" type="submit">
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
