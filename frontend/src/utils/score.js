// Escala secuencial violeta (oscuro = score alto, claro = score bajo).
// Verde/rojo se reservan exclusivamente para variaciones (subió/bajó) —
// nunca para representar el nivel de score en sí.
const VIOLET_SCALE = ["#b6a8fb", "#9a86fa", "#7f66f8", "#5b3df5", "#4a30dc", "#3a24b8"];

export function violetForScore(score) {
  if (score === null || score === undefined) return "#d8d2f6";
  const idx = Math.min(5, Math.max(0, Math.floor((score / 100) * 6)));
  return VIOLET_SCALE[idx];
}

export function textOnScore(score) {
  if (score === null || score === undefined) return "#5e5885";
  const idx = Math.min(5, Math.max(0, Math.floor((score / 100) * 6)));
  return idx >= 2 ? "#ffffff" : "#1e1640";
}

export function formatScore(score) {
  if (score === null || score === undefined) return "—";
  return score.toFixed(1);
}

export function scoreLabel(score) {
  if (score === null || score === undefined) return "Sin evaluar";
  if (score >= 70) return "Alta oportunidad";
  if (score >= 45) return "Oportunidad media";
  return "Baja oportunidad";
}

/** Delta vs. una evaluación anterior — esto SÍ usa semántica subió/bajó. */
export function delta(actual, anterior) {
  if (actual === null || actual === undefined || anterior === null || anterior === undefined) return null;
  return actual - anterior;
}
