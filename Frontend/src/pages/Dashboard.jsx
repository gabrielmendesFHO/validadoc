import { useState } from "react";
import { FileUp, LogOut, Search, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

// Dados de exemplo — troque por dados vindos da sua API quando estiver pronta.
const MOCK_STATS = {
  ultimasValidacoesHoje: 4,
  statusGeral: { label: "Aprovado", percent: 72 },
  totalValidacoes: 1234,
};

const MOCK_HISTORICO = [
  { id: 1, data: "27/11/2025", hora: "11:35", tipo: "RG", resultado: "Aprovado" },
  { id: 2, data: "26/11/2025", hora: "15:23", tipo: "CPF", resultado: "Rejeitado" },
];

function Badge({ resultado }) {
  const isAprovado = resultado === "Aprovado";
  return (
    <span className={`status-badge ${isAprovado ? "status-approved" : "status-rejected"}`}>
      {resultado}
    </span>
  );
}

export default function Dashboard({
  usuario,
  onLogout,
  stats = MOCK_STATS,
  historico = MOCK_HISTORICO,
}) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState("");

  function abrirAuditoria(event) {
    event.preventDefault();
    if (inscricaoId.trim()) navigate(`/auditoria/${inscricaoId.trim()}`);
  }

  const primeiroNome = usuario?.nome_completo?.split(" ")[0] || "User";
  const podeConsultar = usuario?.perfil !== "CANDIDATO";

  return (
    <main className="dash-shell">
      <header className="dash-topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <ShieldCheck size={18} />
          </div>
          <strong>ValidaDoc</strong>
        </div>
        <button className="icon-button" onClick={onLogout} title="Sair">
          <LogOut size={17} />
        </button>
      </header>

      <section className="dash-card">
        <div className="dash-heading">
          <div>
            <h1>Bem-vindo, {primeiroNome}</h1>
            <p className="muted">Inicie uma validação ou confira o histórico.</p>
          </div>
          <button className="primary-button" onClick={() => navigate("/upload")}>
            <FileUp size={16} /> Validar documento
          </button>
        </div>

        <div className="summary-grid">
          <article className="summary-card">
            <span className="summary-title">Últimas validações</span>
            <p className="muted small">Visualize resultados recentes.</p>
            <p className="summary-line">
              Hoje: <strong>{stats.ultimasValidacoesHoje}</strong>
            </p>
          </article>

          <article className="summary-card">
            <span className="summary-title">Status Geral</span>
            <div className="summary-status-row">
              <span className="status-badge status-approved">{stats.statusGeral.label}</span>
              <strong>{stats.statusGeral.percent}%</strong>
            </div>
          </article>

          <article className="summary-card">
            <span className="summary-title">Contagem</span>
            <p className="summary-line">
              Validações Totais: <strong>{stats.totalValidacoes}</strong>
            </p>
          </article>
        </div>

        {podeConsultar && (
          <form className="inline-search" onSubmit={abrirAuditoria}>
            <label htmlFor="inscricao-id">Consultar parecer por inscrição</label>
            <div className="input-action">
              <input
                id="inscricao-id"
                value={inscricaoId}
                onChange={(event) => setInscricaoId(event.target.value)}
                placeholder="Ex.: 3"
                inputMode="numeric"
                required
              />
              <button className="icon-button" type="submit" title="Consultar">
                <Search size={16} />
              </button>
            </div>
          </form>
        )}

        <h2 className="section-title">Histórico Recente</h2>

        <table className="history-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {historico.map((item) => (
              <tr key={item.id}>
                <td>
                  {item.data} {item.hora}
                </td>
                <td>{item.tipo}</td>
                <td>
                  <Badge resultado={item.resultado} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}