import { useEffect, useState } from "react";
import { FileUp, LogOut, Search, ShieldCheck, UserPlus, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import "./Dashboard.css";

function Badge({ resultado }) {
  let classe = "status-neutral";
  if (resultado === "Aprovado") classe = "status-approved";
  else if (resultado === "Rejeitado") classe = "status-rejected";
  else if (resultado === "Atenção" || resultado === "Erro IA") classe = "status-warning";
  else if (resultado === "Processando") classe = "status-processing";

  return (
    <span className={`status-badge ${classe}`}>
      {resultado}
    </span>
  );
}

export default function Dashboard({
  usuario,
  onLogout,
}) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState("");
  const [stats, setStats] = useState({
    ultimasValidacoesHoje: 0,
    statusGeral: { label: "Pendente", percent: 0 },
    totalValidacoes: 0,
  });
  const [historico, setHistorico] = useState([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    async function carregarMetricas() {
      try {
        const { data } = await api.get("/inscricoes/dashboard/metricas");
        if (data.stats) setStats(data.stats);
        if (data.historico) setHistorico(data.historico);
      } catch (err) {
        console.error("Erro ao carregar métricas do dashboard:", err);
      } finally {
        setCarregando(false);
      }
    }
    carregarMetricas();
  }, []);

  function abrirAuditoria(event) {
    event.preventDefault();
    if (inscricaoId.trim()) navigate(`/auditoria/${inscricaoId.trim()}`);
  }

  const primeiroNome = usuario?.nome_completo?.split(" ")[0] || "Usuário";
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
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {usuario?.perfil === "ADMIN" && (
              <button
                className="primary-button"
                onClick={() => navigate("/pre-cadastro")}
                style={{ background: "#6366f1" }}
              >
                <UserPlus size={16} /> Pré-cadastrar candidato
              </button>
            )}
            <button className="primary-button" onClick={() => navigate("/upload")}>
              <FileUp size={16} /> Validar documento
            </button>
            {usuario?.perfil === "CANDIDATO" && (
              <button className="primary-button" onClick={() => navigate("/familia")} style={{ background: "#10b981" }}>
                <Users size={16} /> Membros da família
              </button>
            )}
          </div>
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
              <span className={`status-badge ${
                stats.statusGeral.label === "Aprovado"
                  ? "status-approved"
                  : stats.statusGeral.label === "Rejeitado"
                  ? "status-rejected"
                  : stats.statusGeral.label === "Em Análise"
                  ? "status-warning"
                  : "status-neutral"
              }`}>
                {stats.statusGeral.label}
              </span>
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
            {historico.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ textAlign: "center", color: "#9ca3af", padding: "28px 0", fontSize: 14 }}>
                  {carregando ? "Carregando histórico..." : "Nenhum documento enviado ainda."}
                </td>
              </tr>
            ) : (
              historico.map((item) => (
                <tr key={item.id}>
                  <td>
                    {item.data} {item.hora}
                  </td>
                  <td>{item.tipo}</td>
                  <td>
                    <Badge resultado={item.resultado} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}