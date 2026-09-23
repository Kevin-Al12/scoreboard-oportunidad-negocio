import { useEffect, useState } from "react";
import { Copy, KeyRound, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [nombre, setNombre] = useState("");
  const [nuevaKey, setNuevaKey] = useState(null);
  const [error, setError] = useState(null);

  function cargar() {
    api.listarApiKeys().then(setKeys).catch((e) => setError(e.message));
  }

  useEffect(cargar, []);

  async function crear(e) {
    e.preventDefault();
    try {
      const creada = await api.crearApiKey(nombre || "Sin nombre");
      setNuevaKey(creada.api_key);
      setNombre("");
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function revocar(id) {
    if (!confirm("¿Revocar esta API key? Cualquier integración que la use dejará de funcionar de inmediato.")) return;
    try {
      await api.revocarApiKey(id);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Para integraciones externas" title="API keys" />

      {error && <div className="error-banner">{error}</div>}

      <div className="card tint">
        <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-muted)" }}>
          Autentica llamadas a la API sin sesión de usuario, mandando la clave en el header{" "}
          <code>X-API-Key</code>. Sujeta a un límite de solicitudes por minuto (ver README —
          rate limiting de demostración, en memoria de proceso).
        </p>
      </div>

      {nuevaKey && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <h3 style={{ marginBottom: 8 }}>Copia esta clave ahora</h3>
          <p className="muted" style={{ marginTop: 0 }}>No se puede volver a mostrar completa una vez que cierres esto.</p>
          <div className="row" style={{ background: "var(--surface-sunken, var(--bg))", padding: "10px 14px", borderRadius: 10 }}>
            <code style={{ flex: 1, wordBreak: "break-all" }}>{nuevaKey}</code>
            <button
              className="icon-btn"
              onClick={() => {
                navigator.clipboard?.writeText(nuevaKey);
              }}
              aria-label="Copiar"
            >
              <Copy size={15} />
            </button>
          </div>
          <button className="btn secondary sm" style={{ marginTop: 12 }} onClick={() => setNuevaKey(null)}>
            Listo, ya la copié
          </button>
        </div>
      )}

      <div className="card" style={{ padding: 8 }}>
        {keys.length === 0 ? (
          <div className="empty-state">No tienes API keys todavía.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Prefijo</th>
                <th>Creada</th>
                <th>Último uso</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td style={{ fontWeight: 600 }}>{k.nombre}</td>
                  <td>
                    <code>{k.prefijo}…</code>
                  </td>
                  <td className="muted">{new Date(k.creado_en).toLocaleDateString()}</td>
                  <td className="muted">{k.ultimo_uso_en ? new Date(k.ultimo_uso_en).toLocaleString() : "Nunca"}</td>
                  <td>
                    <span className={`badge ${k.revocada ? "critical" : "good"}`}>
                      <span className="dot" /> {k.revocada ? "Revocada" : "Activa"}
                    </span>
                  </td>
                  <td>
                    {!k.revocada && (
                      <button className="icon-btn" style={{ width: 36, height: 36 }} onClick={() => revocar(k.id)}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 14 }}>
          <KeyRound size={16} style={{ marginRight: 7, verticalAlign: -3 }} />
          Nueva API key
        </h3>
        <form onSubmit={crear} className="row">
          <input
            placeholder="Ej. Integración con Zapier"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            style={{ flex: 1, minWidth: 220 }}
          />
          <button className="btn" type="submit">
            Generar
          </button>
        </form>
      </div>
    </div>
  );
}
