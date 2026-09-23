import { useEffect, useState } from "react";
import { Copy, Mail, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../auth/AuthContext";

const ROLES = ["admin", "editor", "viewer"];

export default function EquipoPage() {
  const { usuario: yo } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [invitaciones, setInvitaciones] = useState([]);
  const [organizacion, setOrganizacion] = useState(null);
  const [nuevoInviteEmail, setNuevoInviteEmail] = useState("");
  const [nuevoInviteRole, setNuevoInviteRole] = useState("viewer");
  const [slackUrl, setSlackUrl] = useState("");
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  function cargar() {
    api.listarUsuarios().then(setUsuarios).catch((e) => setError(e.message));
    api.listarInvitaciones().then(setInvitaciones).catch((e) => setError(e.message));
    api.obtenerOrganizacion().then((org) => {
      setOrganizacion(org);
      // La API ya no devuelve la URL completa del webhook (funciona como
      // contraseña) -- el campo arranca vacío y solo se manda si escribes una nueva.
      setSlackUrl("");
    });
  }

  useEffect(cargar, []);

  async function cambiarRol(id, role) {
    try {
      await api.actualizarUsuario(id, { role });
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggleActivo(u) {
    try {
      await api.actualizarUsuario(u.id, { activo: !u.activo });
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function invitar(e) {
    e.preventDefault();
    setAviso(null);
    try {
      const inv = await api.crearInvitacion(nuevoInviteEmail, nuevoInviteRole);
      setNuevoInviteEmail("");
      setAviso(`Invitación creada. Código: ${inv.token}`);
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function revocarInvitacion(id) {
    await api.revocarInvitacion(id);
    cargar();
  }

  async function guardarSlack(e) {
    e.preventDefault();
    if (!slackUrl.trim()) return;
    setError(null);
    try {
      await api.actualizarOrganizacion({ slack_webhook_url: slackUrl.trim() });
      setAviso("Webhook de Slack guardado.");
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function quitarSlack() {
    setError(null);
    try {
      await api.actualizarOrganizacion({ slack_webhook_url: null });
      setAviso("Webhook de Slack eliminado.");
      cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <PageHeader eyebrow={organizacion ? organizacion.nombre : "Roles y permisos"} title="Equipo" />

      {error && <div className="error-banner">{error}</div>}
      {aviso && (
        <div className="card tint" style={{ padding: 14 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600, fontSize: 13.5 }}>{aviso}</span>
            <button
              className="icon-btn"
              style={{ width: 32, height: 32 }}
              onClick={() => {
                navigator.clipboard?.writeText(aviso.split(": ").pop());
              }}
            >
              <Copy size={13} />
            </button>
          </div>
        </div>
      )}

      <div className="card tint">
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-muted)", fontWeight: 600 }}>
          <strong>admin</strong>: todo, incluyendo borrar criterios y cambiar roles · <strong>editor</strong>:
          crea/edita sectores, criterios y evaluaciones · <strong>viewer</strong>: solo lectura y comentarios.
        </p>
      </div>

      <div className="card" style={{ padding: 8 }}>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Email</th>
              <th>Rol</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td style={{ fontWeight: 600 }}>{u.nombre_completo}</td>
                <td className="muted">{u.email}</td>
                <td>
                  <select value={u.role} onChange={(e) => cambiarRol(u.id, e.target.value)} disabled={u.id === yo.id}>
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <label className="row" style={{ gap: 6, cursor: u.id === yo.id ? "default" : "pointer" }}>
                    <input type="checkbox" checked={u.activo} disabled={u.id === yo.id} onChange={() => toggleActivo(u)} />
                    <span className="muted">{u.activo ? "Activo" : "Desactivado"}</span>
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 4 }}>
          <Mail size={16} style={{ marginRight: 7, verticalAlign: -3 }} />
          Invitar a alguien
        </h3>
        <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
          Es la única forma de sumar a alguien a tu organización — ya no se puede entrar solo
          escribiendo el nombre de la empresa. El código queda atado a este email exacto.
        </p>
        <form onSubmit={invitar} className="row" style={{ marginBottom: 20 }}>
          <input
            type="email"
            required
            placeholder="email@empresa.com"
            value={nuevoInviteEmail}
            onChange={(e) => setNuevoInviteEmail(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <select value={nuevoInviteRole} onChange={(e) => setNuevoInviteRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button className="btn" type="submit">
            Invitar
          </button>
        </form>

        {invitaciones.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Rol</th>
                <th>Código</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invitaciones.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.email}</td>
                  <td className="muted">{inv.role}</td>
                  <td>
                    <code style={{ fontSize: 11 }}>{inv.token.slice(0, 16)}…</code>
                  </td>
                  <td>
                    <span className={`badge ${inv.usada ? "neutral" : "good"}`}>
                      <span className="dot" /> {inv.usada ? "Usada" : "Pendiente"}
                    </span>
                  </td>
                  <td>
                    {!inv.usada && (
                      <button className="icon-btn" style={{ width: 32, height: 32 }} onClick={() => revocarInvitacion(inv.id)}>
                        <Trash2 size={12} />
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
        <h3 style={{ marginBottom: 4 }}>Notificaciones a Slack</h3>
        <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
          Webhook propio de <strong>tu</strong> organización — nunca se comparte con otras (ver README).
        </p>
        <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
          {organizacion?.slack_configurado
            ? `Configurado: ${organizacion.slack_webhook_mascara}`
            : "Sin webhook configurado."}
        </p>
        <form onSubmit={guardarSlack} className="row">
          <input
            placeholder={
              organizacion?.slack_configurado
                ? "Pega un webhook nuevo para reemplazarlo"
                : "https://hooks.slack.com/services/..."
            }
            value={slackUrl}
            onChange={(e) => setSlackUrl(e.target.value)}
            style={{ flex: 1, minWidth: 260 }}
          />
          <button className="btn secondary" type="submit" disabled={!slackUrl.trim()}>
            Guardar
          </button>
          {organizacion?.slack_configurado && (
            <button className="btn secondary" type="button" onClick={quitarSlack}>
              Quitar
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
