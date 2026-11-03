import { ClipboardCheck, ClipboardList, LayoutDashboard, LogOut, ShieldCheck, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import api from "../api/client";
import "./PortalLayouts.css";
const nav = [["/dashboard", "Dashboard", LayoutDashboard], ["/fila-auditoria", "Fila de auditoria", ClipboardCheck], ["/pre-cadastro", "Pré-cadastro", UserPlus]];
const nivelJornada = { PRE_CADASTRADO: 0, KYC_PENDENTE: 1, KYC_VALIDADO: 2, FAMILIA_PENDENTE: 2, DOCS_PENDENTES: 3, PRONTO_AUDITORIA: 4, CONCLUIDO: 5, ABANDONO: 5 };

export function CandidateTopbar({ title, onLogout }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  useEffect(() => {
    let ativo = true;
    api.get("/inscricoes/minha/jornada")
      .then(({ data }) => { if (ativo) setStatus(data.status_funil); })
      .catch(() => {});
    return () => { ativo = false; };
  }, []);
  const nivel = nivelJornada[status] ?? 0;
  return <header className="candidate-topbar"><button className="logo-button" onClick={() => navigate("/acompanhamento")}><ShieldCheck /> ValidaDoc</button><nav className="candidate-nav"><NavLink to="/acompanhamento">Acompanhamento</NavLink>{nivel >= 2 && <NavLink to="/familia">Familiares</NavLink>}{nivel >= 3 && <NavLink to="/dashboard"><ClipboardList size={15}/> Comprovantes</NavLink>}</nav><div><span>{title}</span><button className="quiet-button" onClick={onLogout}>Sair <LogOut size={16} /></button></div></header>;
}
export function AnalystLayout({ children, onLogout }) {
  return (
    <main className="sidebar-layout">
      <aside className="sidebar-nav">
        <div className="sidebar-logo">
          <span className="sidebar-brand-icon" aria-hidden="true"><ShieldCheck size={23} strokeWidth={1.8}/></span>
          <span>ValidaDoc</span>
        </div>
        <p>PORTAL DO ANALISTA</p>
        <nav className="sidebar-menu" aria-label="Portal do analista">
          {nav.map(([to, label, Icon]) => (
            <NavLink key={label} to={to} className="sidebar-nav-item">
              <span className="sidebar-nav-icon" aria-hidden="true"><Icon size={20} strokeWidth={1.8}/></span>
              <span className="sidebar-nav-label">{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="sidebar-exit" onClick={onLogout}>
          <span className="sidebar-nav-icon" aria-hidden="true"><LogOut size={20} strokeWidth={1.8}/></span>
          <span className="sidebar-nav-label">Sair</span>
        </button>
      </aside>
      <section className="analyst-content">{children}</section>
    </main>
  );
}
