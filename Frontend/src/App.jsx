import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Auditoria from "./pages/Auditoria";
import PreCadastro from "./pages/PreCadastro";
import Familia from "./pages/Familia";
import KYC from "./pages/KYC";
import Acompanhamento from "./pages/Acompanhamento";
import FilaAuditoria from "./pages/FilaAuditoria";
import DetalheInscricao from "./pages/DetalheInscricao";

function RotaProtegida({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

function RotaAdmin({ children }) {
  const token = localStorage.getItem("access_token");
  const usuario = JSON.parse(localStorage.getItem("usuario") || "null");
  if (!token) return <Navigate to="/login" replace />;
  if (usuario?.perfil !== "ADMIN") return <Navigate to="/dashboard" replace />;
  return children;
}

function usuarioAtual() {
  return JSON.parse(localStorage.getItem("usuario") || "null");
}

function limparSessao() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("usuario");
}

export default function App() {
  const [usuario, setUsuario] = useState(usuarioAtual);

  function logout() {
    limparSessao();
    window.location.assign("/login");
  }

  function concluirLogin(usuarioAutenticado) {
    setUsuario(usuarioAutenticado);
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login onLogin={concluirLogin} />} />
        <Route
          path="/dashboard"
          element={
            <RotaProtegida>
              <Dashboard usuario={usuario} onLogout={logout} />
            </RotaProtegida>
          }
        />
        <Route path="/upload" element={<Navigate to="/dashboard" replace />} />
        <Route path="/kyc" element={<RotaProtegida><KYC onLogout={logout} /></RotaProtegida>} />
        <Route path="/acompanhamento" element={<RotaProtegida><Acompanhamento onLogout={logout} /></RotaProtegida>} />
        <Route path="/familia" element={<RotaProtegida><Familia usuario={usuario} onLogout={logout} /></RotaProtegida>} />
        <Route path="/auditoria/:inscricaoId" element={<RotaProtegida><Auditoria usuario={usuario} onLogout={logout} /></RotaProtegida>} />
        <Route path="/fila-auditoria" element={<RotaProtegida><FilaAuditoria onLogout={logout} /></RotaProtegida>} />
        <Route path="/detalhe/:inscricaoId" element={<RotaProtegida><DetalheInscricao onLogout={logout} /></RotaProtegida>} />
        <Route
          path="/pre-cadastro"
          element={
            <RotaAdmin>
          <PreCadastro onLogout={logout} />
            </RotaAdmin>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
