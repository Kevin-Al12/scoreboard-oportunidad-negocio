import { Route, Routes, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import RequireAuth from "./components/RequireAuth";
import LoginPage from "./pages/LoginPage";
import SectoresPage from "./pages/SectoresPage";
import SectorDetallePage from "./pages/SectorDetallePage";
import CriteriosPage from "./pages/CriteriosPage";
import DashboardPage from "./pages/DashboardPage";
import AuditoriaPage from "./pages/AuditoriaPage";
import ApiKeysPage from "./pages/ApiKeysPage";
import EquipoPage from "./pages/EquipoPage";

function Shell({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-area">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Shell>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/sectores" element={<SectoresPage />} />
                <Route path="/sectores/:id" element={<SectorDetallePage />} />
                <Route path="/criterios" element={<CriteriosPage />} />
                <Route path="/auditoria" element={<AuditoriaPage />} />
                <Route path="/api-keys" element={<ApiKeysPage />} />
                <Route
                  path="/equipo"
                  element={
                    <RequireAuth soloAdmin>
                      <EquipoPage />
                    </RequireAuth>
                  }
                />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Shell>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
