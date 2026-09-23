const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "scoreboard_token";

let onUnauthorized = () => {};
export function setOnUnauthorized(fn) {
  onUnauthorized = fn;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  // FormData (subida de archivos) no debe llevar Content-Type manual -- el
  // navegador tiene que fijar el boundary del multipart él mismo.
  const esFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = {
    ...(options.body && !esFormData ? { "Content-Type": "application/json" } : {}),
    ...options.headers,
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    onUnauthorized();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // respuesta sin cuerpo JSON, se mantiene el statusText
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Como request(), pero también devuelve el total real (header X-Total-Count)
 * -- para listas que soportan limit/offset sin romper las llamadas simples
 * que esperan un array plano (ver listarSectores). */
async function requestConTotal(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    onUnauthorized();
  }
  if (!res.ok) throw new Error(`Error ${res.status} en ${path}`);
  const total = Number(res.headers.get("X-Total-Count") ?? 0);
  return { items: await res.json(), total };
}

async function requestBlob(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (res.status === 401) {
    clearToken();
    onUnauthorized();
  }
  if (!res.ok) throw new Error(`Error ${res.status} descargando ${path}`);
  return res.blob();
}

function descargarBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  baseUrl: BASE_URL,

  // --- Auth ---
  registro: (data) => request("/auth/registro", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request("/auth/me"),

  // --- Usuarios ---
  listarUsuarios: () => request("/usuarios"),
  actualizarUsuario: (id, data) => request(`/usuarios/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // --- Invitaciones (única forma real de unirse a una organización existente) ---
  listarInvitaciones: () => request("/invitaciones"),
  crearInvitacion: (email, role) => request("/invitaciones", { method: "POST", body: JSON.stringify({ email, role }) }),
  revocarInvitacion: (id) => request(`/invitaciones/${id}`, { method: "DELETE" }),

  // --- Organización (config a nivel de tenant, ej. webhook de Slack) ---
  obtenerOrganizacion: () => request("/organizacion"),
  actualizarOrganizacion: (data) => request("/organizacion", { method: "PATCH", body: JSON.stringify(data) }),

  // --- Sectores ---
  listarSectores: (opts = {}) => {
    const params = new URLSearchParams(Object.entries(opts).filter(([, v]) => v !== "" && v != null));
    const qs = params.toString();
    return request(`/sectores${qs ? `?${qs}` : ""}`);
  },
  /** Igual que listarSectores, pero con limit/offset y el total real
   * (X-Total-Count) para armar paginación de verdad en la tabla. */
  listarSectoresPaginado: ({ limit, offset = 0, responsable_id } = {}) => {
    const params = new URLSearchParams(
      Object.entries({ limit, offset, responsable_id }).filter(([, v]) => v !== "" && v != null)
    );
    return requestConTotal(`/sectores?${params.toString()}`);
  },
  obtenerSector: (id) => request(`/sectores/${id}`),
  crearSector: (data) => request("/sectores", { method: "POST", body: JSON.stringify(data) }),
  actualizarSector: (id, data) =>
    request(`/sectores/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  eliminarSector: (id) => request(`/sectores/${id}`, { method: "DELETE" }),

  // --- Criterios ---
  listarCriterios: (opts = {}) =>
    request(`/criterios${opts.solo_activos ? "?solo_activos=true" : ""}`),
  crearCriterio: (data) => request("/criterios", { method: "POST", body: JSON.stringify(data) }),
  actualizarCriterio: (id, data) =>
    request(`/criterios/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  eliminarCriterio: (id) => request(`/criterios/${id}`, { method: "DELETE" }),

  // --- Rondas de evaluación ---
  listarRondas: (sectorId) => request(`/sectores/${sectorId}/rondas`),
  obtenerRonda: (sectorId, rondaId) => request(`/sectores/${sectorId}/rondas/${rondaId}`),
  crearRonda: (sectorId, data) =>
    request(`/sectores/${sectorId}/rondas`, { method: "POST", body: JSON.stringify(data) }),
  eliminarRonda: (sectorId, rondaId) =>
    request(`/sectores/${sectorId}/rondas/${rondaId}`, { method: "DELETE" }),

  // --- Dashboard ---
  ranking: (filtros = {}) => {
    const params = new URLSearchParams(
      Object.entries(filtros).filter(([, v]) => v !== "" && v !== null && v !== undefined)
    );
    const qs = params.toString();
    return request(`/dashboard/ranking${qs ? `?${qs}` : ""}`);
  },
  radarDeSector: (sectorId) => request(`/dashboard/sectores/${sectorId}/radar`),
  historicoDeSector: (sectorId) => request(`/dashboard/sectores/${sectorId}/historico`),

  // --- Reportes: requiere auth, así que se descarga como blob (un <a href>
  // normal no puede mandar el header Authorization). ---
  descargarReportePDF: async (n) => {
    const blob = await requestBlob(`/reportes/top-sectores.pdf?n=${n}`);
    descargarBlob(blob, `top-${n}-sectores.pdf`);
  },

  // --- Auditoría ---
  listarAuditoria: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== "")).toString();
    return request(`/auditoria${qs ? `?${qs}` : ""}`);
  },
  revertirAuditoria: (id) => request(`/auditoria/${id}/revertir`, { method: "POST" }),

  // --- Comentarios ---
  listarComentarios: (sectorId) => request(`/sectores/${sectorId}/comentarios`),
  crearComentario: (sectorId, texto) =>
    request(`/sectores/${sectorId}/comentarios`, { method: "POST", body: JSON.stringify({ texto }) }),
  eliminarComentario: (sectorId, comentarioId) =>
    request(`/sectores/${sectorId}/comentarios/${comentarioId}`, { method: "DELETE" }),

  // --- Notificaciones ---
  listarNotificaciones: (soloNoLeidas = false) =>
    request(`/notificaciones${soloNoLeidas ? "?solo_no_leidas=true" : ""}`),
  marcarNotificacionLeida: (id) => request(`/notificaciones/${id}/leer`, { method: "POST" }),
  marcarTodasLeidas: () => request("/notificaciones/leer-todas", { method: "POST" }),

  // --- API keys ---
  listarApiKeys: () => request("/api-keys"),
  crearApiKey: (nombre) => request("/api-keys", { method: "POST", body: JSON.stringify({ nombre }) }),
  revocarApiKey: (id) => request(`/api-keys/${id}`, { method: "DELETE" }),

  // --- Filtros guardados ---
  listarFiltrosGuardados: () => request("/filtros-guardados"),
  guardarFiltro: (nombre, params) =>
    request("/filtros-guardados", { method: "POST", body: JSON.stringify({ nombre, params }) }),
  eliminarFiltroGuardado: (id) => request(`/filtros-guardados/${id}`, { method: "DELETE" }),

  // --- Contexto de mercado (conector externo real) ---
  indicadoresMacro: () => request("/contexto-mercado/indicadores-macro"),

  // --- Import/export masivo ---
  exportarSectoresCSV: async () => descargarBlob(await requestBlob("/sectores/exportar.csv"), "sectores.csv"),
  exportarSectoresExcel: async () => descargarBlob(await requestBlob("/sectores/exportar.xlsx"), "sectores.xlsx"),
  importarSectores: async (archivo) => {
    const formData = new FormData();
    formData.append("archivo", archivo);
    return request("/sectores/importar", { method: "POST", body: formData });
  },
};
