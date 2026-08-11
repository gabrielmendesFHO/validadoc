import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import UploadDocumento from "./pages/UploadDocumento";
import Auditoria from "./pages/Auditoria";

function RotaProtegida({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

function usuarioAtual() {
  return JSON.parse(localStorage.getItem("usuario") || "null");
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("usuario");
  window.location.assign("/login");
}

export default function App() {
  const usuario = usuarioAtual();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <RotaProtegida>
              <Dashboard usuario={usuario} onLogout={logout} />
            </RotaProtegida>
          }
        />
        <Route path="/upload" element={<RotaProtegida><UploadDocumento usuario={usuario} onLogout={logout} /></RotaProtegida>} />
        <Route path="/auditoria/:inscricaoId" element={<RotaProtegida><Auditoria usuario={usuario} onLogout={logout} /></RotaProtegida>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}