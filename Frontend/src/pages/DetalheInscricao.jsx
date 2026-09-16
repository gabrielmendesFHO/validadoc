import { useEffect, useState } from "react";
import { Check, FileText, AlertTriangle } from "lucide-react";
import { useParams } from "react-router-dom";
import { AnalystLayout } from "../components/PortalLayouts";
import api from "../api/client";

export default function DetalheInscricao({ onLogout }) {
  const { inscricaoId } = useParams();
  const [activeTab, setActiveTab] = useState("dados");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchDetalhes() {
      try {
        const response = await api.get(`/inscricoes/${inscricaoId}/detalhe`);
        setData(response.data);
      } catch (err) {
        setError("Não foi possível carregar os detalhes.");
      } finally {
        setLoading(false);
      }
    }
    fetchDetalhes();
  }, [inscricaoId]);

  if (loading) return <AnalystLayout onLogout={onLogout}><div className="analyst-page"><p>Carregando...</p></div></AnalystLayout>;
  if (error) return <AnalystLayout onLogout={onLogout}><div className="analyst-page"><p>{error}</p></div></AnalystLayout>;

  const { inscricao, candidato, processo, membros, documentos_enviados } = data;

  const steps = ["PRE_CADASTRADO", "KYC_PENDENTE", "FAMILIA_PENDENTE", "DOCS_PENDENTES", "PRONTO_AUDITORIA", "CONCLUIDO"];
  const stepLabels = ["Pré-cadastro", "KYC", "Família", "Documentos", "Auditoria"];
  const currentStepIndex = steps.indexOf(inscricao.status_funil);

  return (
    <AnalystLayout onLogout={onLogout}>
      <div className="analyst-page">
        <header>
          <div>
            <p className="eyebrow">INSCRIÇÃO #{inscricao.id}</p>
            <h1>Detalhe da Inscrição</h1>
            <p className="muted">Dados consolidados do candidato e sua jornada.</p>
          </div>
          <span className="status-chip">{inscricao.status_geral}</span>
        </header>

        <section className="data-panel detail-summary">
          <div>
            <span>Candidato</span>
            <strong>{candidato.nome}</strong>
          </div>
          <div>
            <span>CPF</span>
            <strong>{candidato.cpf || "Não informado"}</strong>
          </div>
          <div>
            <span>Edital</span>
            <strong>{processo.edital}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{inscricao.status_geral}</strong>
          </div>
        </section>

        <section className="data-panel">
          <nav className="detail-tabs">
            <button className={activeTab === "dados" ? "active" : ""} onClick={() => setActiveTab("dados")}>Dados do Candidato</button>
            <button className={activeTab === "familia" ? "active" : ""} onClick={() => setActiveTab("familia")}>Grupo Familiar</button>
            <button className={activeTab === "documentos" ? "active" : ""} onClick={() => setActiveTab("documentos")}>Documentos</button>
            <button className={activeTab === "historico" ? "active" : ""} onClick={() => setActiveTab("historico")}>Histórico</button>
          </nav>

          <div style={{ marginTop: "20px" }}>
            {activeTab === "dados" && (
              <div>
                <h3>Informações Pessoais</h3>
                <p><strong>Nome:</strong> {candidato.nome}</p>
                <p><strong>CPF:</strong> {candidato.cpf || "Não informado"}</p>
                <p><strong>E-mail:</strong> {candidato.email}</p>
                <br />
                <h3>Dados da Inscrição</h3>
                <p><strong>Edital:</strong> {processo.edital}</p>
                <p><strong>Renda Per Capita Calculada:</strong> {inscricao.renda_per_capita_calculada ? `R$ ${inscricao.renda_per_capita_calculada}` : "N/A"}</p>
                <p><strong>Parecer:</strong> {inscricao.parecer || "Nenhum"}</p>
              </div>
            )}

            {activeTab === "familia" && (
              <div>
                <h3>Grupo Familiar ({membros.length} membros)</h3>
                {membros.length === 0 ? <p>Nenhum membro cadastrado.</p> : (
                  <ul style={{ listStyle: "none", padding: 0 }}>
                    {membros.map(m => (
                      <li key={m.id} style={{ borderBottom: "1px solid #eee", padding: "10px 0" }}>
                        <strong>{m.nome_completo}</strong> - {m.parentesco || "Titular"} <br />
                        <span style={{ fontSize: "14px", color: "#666" }}>CPF: {m.cpf || "N/A"} | Renda: R$ {m.renda_declarada || "0.00"}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {activeTab === "documentos" && (
              <div>
                <h3>Documentos Enviados ({documentos_enviados.length})</h3>
                {documentos_enviados.length === 0 ? <p>Nenhum documento enviado.</p> : (
                  <ul style={{ listStyle: "none", padding: 0 }}>
                    {documentos_enviados.map(d => (
                      <li key={d.id} style={{ borderBottom: "1px solid #eee", padding: "10px 0", display: "flex", justifyContent: "space-between" }}>
                        <span>Documento ID: {d.solicitado_id} {d.membro_id ? `(Membro ID: ${d.membro_id})` : "(Titular)"}</span>
                        <span className={`status-pill status-${d.status === 'CONCLUIDO' ? 'good' : 'warn'}`}>{d.status}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <br />
                <button className="brand-button"><FileText size={17} style={{ marginRight: "8px" }} /> Ver todos os documentos</button>
              </div>
            )}

            {activeTab === "historico" && (
              <div>
                <h3>Jornada do Candidato</h3>
                <div className="horizontal-steps" style={{ marginTop: "20px" }}>
                  {stepLabels.map((etapa, i) => {
                    const isComplete = i < currentStepIndex || currentStepIndex === -1;
                    const isCurrent = i === currentStepIndex;
                    return (
                      <div className={isComplete ? "complete" : (isCurrent ? "current" : "")} key={etapa}>
                        <i>{isComplete ? <Check size={13} /> : i + 1}</i>
                        <span>{etapa}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </AnalystLayout>
  );
}
