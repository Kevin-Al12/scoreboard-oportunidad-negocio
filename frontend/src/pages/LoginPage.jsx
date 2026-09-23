import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BarChart3 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login, registrar } = useAuth();
  const navegar = useNavigate();
  const [searchParams] = useSearchParams();
  const [modo, setModo] = useState("login"); // "login" | "registro"
  // "nueva": crear una organización (quedas de admin) — "invitacion": unirte
  // a una existente con el código que te dio un admin de ahí. Ya no existe
  // un tercer modo de "escribe el nombre y entra" -- eso permitía que
  // cualquiera que supiera el nombre de una empresa viera sus datos.
  const [modoOrg, setModoOrg] = useState(searchParams.get("token") ? "invitacion" : "nueva");
  const [form, setForm] = useState({
    email: "",
    password: "",
    nombre_completo: "",
    organizacion_nombre: "",
    token: searchParams.get("token") || "",
  });
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      if (modo === "login") {
        await login(form.email, form.password);
      } else if (modoOrg === "nueva") {
        await registrar({ email: form.email, password: form.password, nombre_completo: form.nombre_completo, organizacion_nombre: form.organizacion_nombre });
      } else {
        await registrar({ email: form.email, password: form.password, nombre_completo: form.nombre_completo, token: form.token });
      }
      navegar("/dashboard");
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <form className="card" onSubmit={enviar} style={{ width: 400, padding: 30 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 22 }}>
          <div className="rail-mark" style={{ width: 36, height: 36 }}>
            <BarChart3 size={17} color="#ff9f6b" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15 }}>Scoreboard</div>
            <div className="muted">Oportunidad de negocio · RD</div>
          </div>
        </div>

        <div className="row" style={{ marginBottom: 18 }}>
          <button
            type="button"
            className={`ph-pill${modo === "login" ? " active" : ""}`}
            style={{ background: modo === "login" ? "var(--violet-900)" : "var(--track)" }}
            onClick={() => setModo("login")}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            className={`ph-pill${modo === "registro" ? " active" : ""}`}
            style={{ background: modo === "registro" ? "var(--violet-900)" : "var(--track)" }}
            onClick={() => setModo("registro")}
          >
            Crear cuenta
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {modo === "registro" && (
          <>
            <div className="field">
              <label>Nombre completo</label>
              <input
                required
                value={form.nombre_completo}
                onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })}
                style={{ width: "100%" }}
              />
            </div>

            <div className="row" style={{ marginBottom: 10 }}>
              <button
                type="button"
                className={`ph-pill${modoOrg === "nueva" ? " active" : ""}`}
                style={{ background: modoOrg === "nueva" ? "var(--violet-900)" : "var(--track)", fontSize: 12.5 }}
                onClick={() => setModoOrg("nueva")}
              >
                Crear organización
              </button>
              <button
                type="button"
                className={`ph-pill${modoOrg === "invitacion" ? " active" : ""}`}
                style={{ background: modoOrg === "invitacion" ? "var(--violet-900)" : "var(--track)", fontSize: 12.5 }}
                onClick={() => setModoOrg("invitacion")}
              >
                Tengo un código de invitación
              </button>
            </div>

            {modoOrg === "nueva" ? (
              <div className="field">
                <label>Nombre de tu organización</label>
                <input
                  required
                  value={form.organizacion_nombre}
                  onChange={(e) => setForm({ ...form, organizacion_nombre: e.target.value })}
                  placeholder="Nombre de tu empresa/equipo"
                  style={{ width: "100%" }}
                />
                <div className="muted" style={{ marginTop: 6 }}>
                  Se crea de cero y quedas como admin. Si tu empresa ya tiene una organización
                  aquí, pídele a un admin que te invite en vez de crear una nueva.
                </div>
              </div>
            ) : (
              <div className="field">
                <label>Código de invitación</label>
                <input
                  required
                  value={form.token}
                  onChange={(e) => setForm({ ...form, token: e.target.value })}
                  placeholder="Te lo da un admin de tu organización"
                  style={{ width: "100%" }}
                />
                <div className="muted" style={{ marginTop: 6 }}>
                  Un admin lo genera desde Equipo → Invitar, atado a tu email exacto.
                </div>
              </div>
            )}
          </>
        )}

        <div className="field">
          <label>Email</label>
          <input
            required
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            style={{ width: "100%" }}
          />
        </div>
        <div className="field" style={{ marginBottom: 20 }}>
          <label>Contraseña</label>
          <input
            required
            type="password"
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            style={{ width: "100%" }}
          />
        </div>

        <button className="btn" type="submit" disabled={cargando} style={{ width: "100%", justifyContent: "center" }}>
          {cargando ? "Un momento..." : modo === "login" ? "Entrar" : "Crear cuenta"}
        </button>

        <p className="muted" style={{ marginTop: 16, textAlign: "center" }}>
          Demo sembrada: admin@acme-analytics.do / Admin123!
        </p>
      </form>
    </div>
  );
}
