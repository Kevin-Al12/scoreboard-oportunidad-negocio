import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, setOnUnauthorized, setToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargarUsuario = useCallback(() => {
    if (!getToken()) {
      setUsuario(null);
      setCargando(false);
      return Promise.resolve();
    }
    // El `return` importa: login()/registrar() hacen `await cargarUsuario()`
    // para no navegar a /dashboard antes de que `usuario` esté seteado. Sin
    // devolver la promesa, ese await no esperaba nada (resolvía de
    // inmediato) y a veces se navegaba con el usuario todavía en null.
    return api
      .me()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => setUsuario(null));
    cargarUsuario();
  }, [cargarUsuario]);

  async function login(email, password) {
    const { access_token } = await api.login({ email, password });
    setToken(access_token);
    await cargarUsuario();
  }

  async function registrar(datos) {
    const { access_token } = await api.registro(datos);
    setToken(access_token);
    await cargarUsuario();
  }

  function logout() {
    clearToken();
    setUsuario(null);
  }

  const puedeEditar = usuario?.role === "admin" || usuario?.role === "editor";
  const esAdmin = usuario?.role === "admin";

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, registrar, logout, puedeEditar, esAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
