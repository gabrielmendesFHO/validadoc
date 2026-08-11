import { useState } from "react";
import { FileCheck2, FileUp, LogOut, Search, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function Dashboard({ usuario, onLogout }) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState("");

  function abrirAuditoria(event) {
    event.preventDefault();
    if (inscricaoId.trim()) navigate(`/auditoria/${inscricaoId.trim()}`);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark"><ShieldCheck size={20} /></div>
          <div><strong>ValidaDoc</strong><span>Centro de validação documental</span></div>
        </div>
        <div className="topbar-user">
          <span>{usuario?.nome_completo}</span>
          <button className="icon-button" onClick={onLogout} title="Sair"><LogOut size={17} /></button>
        </div>
      </header>

      <section className="page-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Visão operacional</p>
            <h1>Dashboard analítico</h1>
            <p className="muted">Acompanhe documentos e pareceres do processo seletivo.</p>
          </div>
          <button className="primary-button" onClick={() => navigate("/upload")}><FileUp size={17} /> Analisar documento</button>
        </div>

        <div className="metric-grid">
          <article className="metric-card"><span>Perfil conectado</span><strong>{usuario?.perfil || "CANDIDATO"}</strong><small>Acesso autenticado</small></article>
          <article className="metric-card accent-blue"><span>Pipeline</span><strong>Ativo</strong><small>Gemini + regras de negócio</small></article>
          <article className="metric-card accent-green"><span>Auditoria</span><strong>Pronta</strong><small>Parecer consolidado disponível</small></article>
        </div>

        <div className="workspace-grid">
          <section className="panel intro-panel">
            <div className="panel-icon"><FileCheck2 size={22} /></div>
            <p className="eyebrow">Fluxo principal</p>
            <h2>Valide um documento com rastreabilidade</h2>
            <p className="muted">Envie RG, comprovante de residência ou holerite. O sistema processa o arquivo e registra a análise no banco.</p>
            <button className="secondary-button" onClick={() => navigate("/upload")}>Abrir envio <FileUp size={16} /></button>
          </section>

          {usuario?.perfil !== "CANDIDATO" && (
            <section className="panel">
              <p className="eyebrow">Área de análise</p>
              <h2>Consultar parecer</h2>
              <p className="muted">Informe o número da inscrição para abrir o resultado consolidado.</p>
              <form className="inline-form" onSubmit={abrirAuditoria}>
                <label htmlFor="inscricao-id">Inscrição</label>
                <div className="input-action"><input id="inscricao-id" value={inscricaoId} onChange={(event) => setInscricaoId(event.target.value)} placeholder="Ex.: 3" inputMode="numeric" required /><button className="primary-button" title="Consultar"><Search size={17} /></button></div>
              </form>
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
