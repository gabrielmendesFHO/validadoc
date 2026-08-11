import { ArrowLeft, AlertTriangle, CheckCircle2, LogOut, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/client";

const STATUS = { APTO: "status-good", NAO_APTO: "status-bad", REVISAO_MANUAL: "status-warn", PENDENTE: "status-warn" };

export default function Auditoria({ usuario, onLogout }) {
  const { inscricaoId } = useParams();
  const navigate = useNavigate();
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    api.post(`/inscricoes/${inscricaoId}/auditar`)
      .then(({ data }) => setResultado(data))
      .catch((error) => setErro(error.response?.data?.detail || "Não foi possível carregar a auditoria."))
      .finally(() => setCarregando(false));
  }, [inscricaoId]);

  return <main className="app-shell">
    <header className="topbar"><div className="brand-lockup"><div className="brand-mark"><ShieldCheck size={20} /></div><div><strong>ValidaDoc</strong><span>Resultado da auditoria</span></div></div><div className="topbar-user"><span>{usuario?.nome_completo}</span><button className="icon-button" onClick={onLogout} title="Sair"><LogOut size={17} /></button></div></header>
    <section className="page-content narrow-content"><button className="back-button" onClick={() => navigate("/dashboard")}><ArrowLeft size={16} /> Dashboard</button><div className="page-heading"><div><p className="eyebrow">Inscrição #{inscricaoId}</p><h1>Resultado da auditoria</h1><p className="muted">Parecer consolidado pelos documentos enviados.</p></div></div>
      {carregando && <div className="panel loading-state">Consultando parecer...</div>}
      {erro && <div className="alert error-alert"><AlertTriangle size={18} /> {erro}</div>}
      {resultado && <div className="audit-grid"><section className="panel result-panel"><div className={`status-pill ${STATUS[resultado.status_geral] || "status-warn"}`}>{resultado.status_geral === "APTO" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />} {resultado.status_geral}</div><p className="eyebrow">Parecer do sistema</p><h2>{resultado.parecer}</h2><div className="income-result"><span>Renda per capita calculada</span><strong>{resultado.renda_per_capita_calculada != null ? `R$ ${Number(resultado.renda_per_capita_calculada).toFixed(2).replace(".", ",")}` : "Não calculada"}</strong></div></section><section className="panel"><p className="eyebrow">Inconsistências</p>{resultado.inconsistencias?.length ? <ul className="issue-list">{resultado.inconsistencias.map((item) => <li key={item}><AlertTriangle size={15} />{item}</li>)}</ul> : <div className="empty-state"><CheckCircle2 size={18} /> Nenhuma inconsistência encontrada.</div>}</section></div>}
    </section>
  </main>;
}
