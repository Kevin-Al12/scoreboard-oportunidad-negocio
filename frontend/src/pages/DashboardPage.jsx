import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
} from "recharts";
import { Download, MoreHorizontal, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { delta, formatScore, violetForScore } from "../utils/score";
import PageHeader from "../components/PageHeader";
import ProgressRing from "../components/ProgressRing";
import SegmentedBar from "../components/SegmentedBar";
import VariationChip from "../components/VariationChip";

const SERIES = ["#3a24b8", "#4a30dc", "#5b3df5", "#7f66f8", "#9a86fa", "#b6a8fb"];
const UMBRAL_OPORTUNIDAD = 70;

export default function DashboardPage() {
  const navegar = useNavigate();

  const [sectores, setSectores] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [criterios, setCriterios] = useState([]);
  const [historicoMap, setHistoricoMap] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [radarActual, setRadarActual] = useState(null);
  const [radarAnterior, setRadarAnterior] = useState(null);
  const [topDetalle, setTopDetalle] = useState(null);
  const [search, setSearch] = useState("");
  const [sortMode, setSortMode] = useState("score_desc");
  const [filtrosScore, setFiltrosScore] = useState({ min_score: "", max_score: "" });
  const [filtrosGuardados, setFiltrosGuardados] = useState([]);
  const [error, setError] = useState(null);

  function cargarRanking(params = {}) {
    api.ranking(params).then(setRanking).catch((e) => setError(e.message));
  }

  useEffect(() => {
    api.listarSectores().then(setSectores).catch((e) => setError(e.message));
    api.listarCriterios().then(setCriterios).catch(() => {});
    cargarRanking();
    api.listarFiltrosGuardados().then(setFiltrosGuardados).catch(() => {});
  }, []);

  function aplicarFiltrosScore() {
    cargarRanking(filtrosScore);
  }

  async function guardarFiltroActual() {
    const nombre = prompt("Nombre para este filtro:");
    if (!nombre) return;
    try {
      const creado = await api.guardarFiltro(nombre, filtrosScore);
      setFiltrosGuardados((prev) => [creado, ...prev]);
    } catch (e) {
      setError(e.message);
    }
  }

  function aplicarFiltroGuardado(f) {
    const params = { min_score: f.params.min_score ?? "", max_score: f.params.max_score ?? "" };
    setFiltrosScore(params);
    cargarRanking(params);
  }

  async function borrarFiltroGuardado(id) {
    await api.eliminarFiltroGuardado(id);
    setFiltrosGuardados((prev) => prev.filter((f) => f.id !== id));
  }

  const evaluados = useMemo(() => sectores.filter((s) => s.score_0_a_100 !== null), [sectores]);
  const topSector = ranking[0] || null;

  useEffect(() => {
    if (topSector && selectedId === null) setSelectedId(topSector.id);
  }, [topSector, selectedId]);

  useEffect(() => {
    if (evaluados.length === 0) return;
    let cancelado = false;
    Promise.all(evaluados.map((s) => api.historicoDeSector(s.id).then((h) => [s.id, h.puntos])))
      .then((pares) => {
        if (cancelado) return;
        setHistoricoMap(Object.fromEntries(pares));
      })
      .catch(() => {});
    return () => {
      cancelado = true;
    };
  }, [evaluados]);

  useEffect(() => {
    if (!topSector) return;
    api.radarDeSector(topSector.id).then(setTopDetalle).catch(() => setTopDetalle(null));
  }, [topSector]);

  useEffect(() => {
    if (!selectedId) return;
    api.radarDeSector(selectedId).then(setRadarActual).catch(() => setRadarActual(null));
    cargarPrevioDetalle(selectedId).then(setRadarAnterior).catch(() => setRadarAnterior(null));
  }, [selectedId]);

  async function cargarPrevioDetalle(sectorId) {
    const rondas = await api.listarRondas(sectorId);
    if (rondas.length < 2) return null;
    return api.obtenerRonda(sectorId, rondas[1].id);
  }

  // ---- Derivados: KPIs ----
  const avgActual = evaluados.length
    ? evaluados.reduce((acc, s) => acc + s.score_0_a_100, 0) / evaluados.length
    : null;

  const comparables = evaluados
    .map((s) => {
      const puntos = historicoMap[s.id];
      if (!puntos || puntos.length < 2) return null;
      return puntos[puntos.length - 2].score_0_a_100;
    })
    .filter((v) => v !== null);

  const avgAnterior = comparables.length ? comparables.reduce((a, b) => a + b, 0) / comparables.length : null;
  const deltaPromedio = delta(avgActual, avgAnterior);

  const sobreUmbral = evaluados.filter((s) => s.score_0_a_100 >= UMBRAL_OPORTUNIDAD).length;
  const pctSobreUmbral = evaluados.length ? (sobreUmbral / evaluados.length) * 100 : 0;

  const topPrevScore = topSector ? historicoMap[topSector.id]?.[historicoMap[topSector.id]?.length - 2]?.score_0_a_100 ?? null : null;
  const topDelta = topSector ? delta(topSector.score_0_a_100, topPrevScore) : null;
  const criterioFuerte = topDetalle?.detalle?.[0];
  const criterioDebil = topDetalle?.detalle?.[topDetalle.detalle.length - 1];

  // ---- Derivados: lista filtrada/ordenada ----
  const listaVisible = useMemo(() => {
    let lista = ranking.filter((s) => s.nombre.toLowerCase().includes(search.toLowerCase()));
    if (sortMode === "score_asc") lista = [...lista].sort((a, b) => a.score_0_a_100 - b.score_0_a_100);
    else if (sortMode === "nombre") lista = [...lista].sort((a, b) => a.nombre.localeCompare(b.nombre));
    else if (sortMode === "reciente")
      lista = [...lista].sort((a, b) => new Date(b.fecha_ultima_evaluacion) - new Date(a.fecha_ultima_evaluacion));
    return lista;
  }, [ranking, search, sortMode]);

  // ---- Derivados: distribución de pesos ----
  const activos = criterios.filter((c) => c.activo).sort((a, b) => a.orden - b.orden);
  const pesoTotal = activos.reduce((acc, c) => acc + c.peso, 0);
  const principales = activos.slice(0, 5);
  const resto = activos.slice(5);
  const pesoResto = resto.reduce((acc, c) => acc + c.peso, 0);
  const segmentosPeso = [
    ...principales.map((c, i) => ({ pct: (c.peso / pesoTotal) * 100, color: SERIES[i], nombre: c.nombre, peso: c.peso })),
    ...(resto.length ? [{ pct: (pesoResto / pesoTotal) * 100, color: "#1e1640", nombre: "Otros", peso: pesoResto }] : []),
  ];

  const datosRadar = (radarActual?.detalle || []).map((d) => {
    const previo = radarAnterior?.detalle?.find((p) => p.criterio_id === d.criterio_id);
    return { criterio: d.criterio_nombre, valorActual: d.valor, valorAnterior: previo ? previo.valor : undefined };
  });

  return (
    <div>
      <PageHeader
        eyebrow={`Datos en vivo · ${evaluados.length} sectores evaluados`}
        title="Dashboard comparativo"
        pills={[
          { label: "Score ↓", active: sortMode === "score_desc", onClick: () => setSortMode("score_desc") },
          { label: "Score ↑", active: sortMode === "score_asc", onClick: () => setSortMode("score_asc") },
          { label: "Nombre", active: sortMode === "nombre", onClick: () => setSortMode("nombre") },
          { label: "Recientes", active: sortMode === "reciente", onClick: () => setSortMode("reciente") },
        ]}
        search={{ value: search, onChange: setSearch, placeholder: "Buscar sector…" }}
        primaryAction={{ label: "Exportar PDF", icon: Download, onClick: () => api.descargarReportePDF(5).catch((e) => setError(e.message)) }}
      />

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ padding: 14 }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="row">
            <span className="muted" style={{ fontWeight: 700 }}>Filtro por score:</span>
            <input
              type="number"
              min={0}
              max={100}
              placeholder="mín"
              value={filtrosScore.min_score}
              onChange={(e) => setFiltrosScore({ ...filtrosScore, min_score: e.target.value })}
              style={{ width: 70 }}
            />
            <span className="muted">—</span>
            <input
              type="number"
              min={0}
              max={100}
              placeholder="máx"
              value={filtrosScore.max_score}
              onChange={(e) => setFiltrosScore({ ...filtrosScore, max_score: e.target.value })}
              style={{ width: 70 }}
            />
            <button className="btn secondary sm" onClick={aplicarFiltrosScore}>
              Aplicar
            </button>
            <button className="btn secondary sm" onClick={guardarFiltroActual}>
              Guardar filtro
            </button>
          </div>
          {filtrosGuardados.length > 0 && (
            <div className="row">
              <span className="muted">Guardados:</span>
              {filtrosGuardados.map((f) => (
                <span key={f.id} className="chip on-dark" style={{ cursor: "pointer" }} onClick={() => aplicarFiltroGuardado(f)}>
                  {f.nombre}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      borrarFiltroGuardado(f.id);
                    }}
                    style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: 0, marginLeft: 4 }}
                    aria-label="Eliminar filtro"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {!topSector ? (
        <div className="card empty-state">Todavía no hay sectores evaluados. Ve a Sectores y registra tu primera evaluación.</div>
      ) : (
        <>
          <section className="bento">
            {/* Hero: sector #1 */}
            <article className="card dark" style={{ gridColumn: "span 7", display: "flex", flexDirection: "column", gap: 20, padding: 24 }}>
              <div
                style={{
                  position: "absolute",
                  right: -60,
                  top: -60,
                  width: 260,
                  height: 260,
                  borderRadius: "50%",
                  border: "44px solid var(--surface-dark-2)",
                }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 10, position: "relative" }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-on-dark-muted)" }}>Sector #1 del ranking</div>
                <span className="chip on-dark">Actual</span>
                <div style={{ flexGrow: 1 }} />
                <button className="icon-btn" style={{ background: "var(--surface-dark-2)", color: "white" }} onClick={() => navegar(`/sectores/${topSector.id}`)} aria-label="Ver detalle">
                  <MoreHorizontal size={18} />
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6, position: "relative" }}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{topSector.nombre}</div>
                <div className="hero-number">
                  {formatScore(topSector.score_0_a_100)}
                  <span style={{ color: "#9c92d6", fontSize: 24, fontWeight: 700 }}> / 100</span>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12, position: "relative" }}>
                <div style={{ position: "relative", height: 18, borderRadius: 999, background: "var(--surface-dark-2)" }}>
                  {topPrevScore !== null && (
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: `${topPrevScore}%`,
                        borderRadius: 999,
                        border: "2px dashed var(--accent)",
                        boxSizing: "border-box",
                      }}
                    />
                  )}
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${topSector.score_0_a_100}%`,
                      borderRadius: 999,
                      background: "var(--violet-400)",
                    }}
                  />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: 16 }}>
                  <MiniMetric label="Criterio más fuerte" value={criterioFuerte ? criterioFuerte.criterio_nombre : "—"} />
                  <MiniMetric label="Criterio más débil" value={criterioDebil ? criterioDebil.criterio_nombre : "—"} />
                  <MiniMetric
                    label="Cambio vs. anterior"
                    value={topDelta !== null ? `${topDelta >= 0 ? "+" : ""}${topDelta.toFixed(1)} pts` : "Primera evaluación"}
                    accent={topDelta !== null}
                  />
                </div>
              </div>
            </article>

            {/* KPIs derecha */}
            <div style={{ gridColumn: "span 5", display: "flex", flexDirection: "column", gap: 20 }}>
              <article className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div className="chip" style={{ background: "var(--violet-100)", color: "var(--violet-600)" }}>
                    <Sparkles size={14} />
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Score promedio</div>
                  <div style={{ flexGrow: 1 }} />
                  <VariationChip value={deltaPromedio} suffix=" pts" />
                </div>
                <div style={{ display: "flex", alignItems: "flex-end", gap: 20 }}>
                  <div className="tile-number">{avgActual !== null ? avgActual.toFixed(1) : "—"}</div>
                  <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: 8, paddingBottom: 4 }}>
                    <BarRow label="Actual" pct={avgActual || 0} color="var(--violet-600)" />
                    <BarRow label="Anterior" pct={avgAnterior || 0} color="var(--violet-200)" />
                  </div>
                </div>
              </article>

              <article className="card violet" style={{ display: "flex", alignItems: "center", gap: 24 }}>
                <ProgressRing value={pctSobreUmbral} trackColor="#4a2fd6" fillColor="var(--accent)">
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{pctSobreUmbral.toFixed(0)}%</div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#dcd4ff" }}>de la meta</div>
                </ProgressRing>
                <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#e6e0ff" }}>Sectores en zona de oportunidad</div>
                  <div className="tile-number">
                    {sobreUmbral} <span style={{ fontSize: 22, fontWeight: 700, color: "#dcd4ff" }}>/ {evaluados.length}</span>
                  </div>
                  <div className="muted" style={{ color: "#dcd4ff" }}>Umbral: score ≥ {UMBRAL_OPORTUNIDAD}</div>
                </div>
              </article>
            </div>
          </section>

          <section className="bento">
            {/* Ranking */}
            <article className="card" style={{ gridColumn: "span 5", display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h2 className="card-title">Ranking de sectores</h2>
                <div style={{ flexGrow: 1 }} />
                <a href="/sectores">Ver todos</a>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "28px 1fr 90px", gap: 12, fontSize: 12, fontWeight: 700, color: "var(--text-muted)", padding: "0 4px" }}>
                <div>#</div>
                <div>Sector</div>
                <div>Score</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {listaVisible.map((s, i) => (
                  <div
                    key={s.id}
                    onClick={() => setSelectedId(s.id)}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "28px 1fr 90px",
                      gap: 12,
                      alignItems: "center",
                      padding: "10px 4px",
                      borderRadius: 16,
                      cursor: "pointer",
                      background: s.id === selectedId ? "#f6f3ff" : "transparent",
                    }}
                  >
                    <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-muted)" }}>{i + 1}</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                      <div className={`avatar${i === 0 ? " leader" : ""}`}>{iniciales(s.nombre)}</div>
                      <div style={{ fontSize: 14.5, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {s.nombre}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="bar-track" style={{ flexGrow: 1, height: 8 }}>
                        <div style={{ width: `${s.score_0_a_100}%`, height: "100%", borderRadius: 999, background: violetForScore(s.score_0_a_100) }} />
                      </div>
                      <div style={{ width: 34, fontSize: 13, fontWeight: 700, textAlign: "right" }}>{s.score_0_a_100.toFixed(0)}</div>
                    </div>
                  </div>
                ))}
                {listaVisible.length === 0 && <div className="empty-state">Sin resultados para "{search}".</div>}
              </div>
            </article>

            {/* Radar comparativo */}
            <article className="card" style={{ gridColumn: "span 4", display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h2 className="card-title" style={{ fontSize: 18 }}>{radarActual?.sector_nombre || "Radar"}</h2>
              </div>
              {radarAnterior && (
                <div className="row" style={{ gap: 16, fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: "var(--violet-600)" }} /> Actual
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 14, borderTop: "2px dashed var(--accent)" }} /> Evaluación anterior
                  </span>
                </div>
              )}
              {datosRadar.length === 0 ? (
                <div className="empty-state">Sin evaluaciones.</div>
              ) : (
                <ResponsiveContainer width="100%" height={230}>
                  <RadarChart data={datosRadar}>
                    <PolarGrid stroke="#e5e0fa" />
                    <PolarAngleAxis dataKey="criterio" tick={{ fontSize: 10.5, fill: "#5e5885" }} />
                    <Radar dataKey="valorActual" stroke="#5b3df5" fill="#5b3df5" fillOpacity={0.25} strokeWidth={2} />
                    {radarAnterior && (
                      <Radar dataKey="valorAnterior" stroke="#ff9f6b" fill="none" strokeWidth={2} strokeDasharray="5 4" />
                    )}
                    <RTooltip formatter={(v) => [`${v} / 5`, ""]} />
                  </RadarChart>
                </ResponsiveContainer>
              )}
            </article>

            {/* Distribución de pesos */}
            <article className="card tint" style={{ gridColumn: "span 3", display: "flex", flexDirection: "column", gap: 14 }}>
              <h2 className="card-title" style={{ fontSize: 18 }}>Distribución de pesos</h2>
              <div className="muted" style={{ color: "var(--text-muted)" }}>{activos.length} criterios activos</div>
              <SegmentedBar segments={segmentosPeso} />
              <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                {segmentosPeso.map((s) => (
                  <div key={s.nombre} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, fontWeight: 600 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color, flexShrink: 0 }} />
                    <div style={{ flexGrow: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.nombre}</div>
                    <div style={{ fontWeight: 800 }}>{s.pct.toFixed(0)}%</div>
                  </div>
                ))}
              </div>
              <div style={{ flexGrow: 1 }} />
              <button className="btn dark" onClick={() => navegar("/criterios")}>Ajustar pesos</button>
            </article>
          </section>
        </>
      )}
    </div>
  );
}

function MiniMetric({ label, value, accent }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "#b3aae6" }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: accent ? "var(--accent)" : "white" }}>{value}</div>
    </div>
  );
}

function BarRow({ label, pct, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 58, fontSize: 12, fontWeight: 600, color: "var(--text-muted)" }}>{label}</div>
      <div className="bar-track" style={{ flexGrow: 1 }}>
        <div style={{ width: `${Math.min(100, pct)}%`, height: "100%", borderRadius: 999, background: color }} />
      </div>
    </div>
  );
}

function iniciales(nombre) {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}
