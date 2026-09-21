import { AlertTriangle, CheckCircle2, ChevronDown, Clock3, FileText, FileUp, Loader2, RefreshCw, Search, UserPlus, UsersRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api/client";
import "./Dashboard.css";
import { AnalystLayout, CandidateTopbar } from "../components/PortalLayouts";

function Badge({ resultado }) { const classe = ["ENVIADO", "Aprovado", "Acessou", "Ativo", "Sem alertas"].includes(resultado) ? "status-approved" : ["REJEITADO", "Erro IA", "Ausente", "Não acessou"].includes(resultado) ? "status-rejected" : resultado === "PROCESSANDO" ? "status-processing" : "status-warning"; return <span className={`status-badge ${classe}`}>{resultado === "ENVIADO" ? "Enviado" : resultado}</span>; }

const STATUS_LABELS = {
  PRE_CADASTRADO: "Pré-cadastro",
  KYC_PENDENTE: "KYC pendente",
  KYC_VALIDADO: "KYC validado",
  FAMILIA_PENDENTE: "Grupo familiar",
  DOCS_PENDENTES: "Documentos",
  PRONTO_AUDITORIA: "Pronto para auditoria",
  CONCLUIDO: "Concluído",
  ABANDONO: "Abandono",
};

const STATUS_COLORS = {
  PRE_CADASTRADO: "#64748b",
  KYC_PENDENTE: "#2563eb",
  KYC_VALIDADO: "#0891b2",
  FAMILIA_PENDENTE: "#7c3aed",
  DOCS_PENDENTES: "#d97706",
  PRONTO_AUDITORIA: "#e11d48",
  CONCLUIDO: "#16803c",
  ABANDONO: "#991b1b",
};

function KpiCard({ icon: Icon, label, value, detail, tone = "green", onClick }) {
  return <button className={`bi-kpi bi-kpi-${tone}`} type="button" onClick={onClick}><span className="bi-kpi-icon"><Icon size={20}/></span><span className="bi-kpi-copy"><small>{label}</small><strong>{value ?? "—"}</strong><em>{detail}</em></span></button>;
}

function DashboardCandidato({ usuario, onLogout }) {
  const [pessoas, setPessoas] = useState([]); const [aberto, setAberto] = useState("candidato"); const [erro, setErro] = useState(""); const [inscricaoId, setInscricaoId] = useState(null); const [enviando, setEnviando] = useState("");
  const carregar = useCallback(async () => { try { const { data: inscricao } = await api.get("/inscricoes/minha"); setInscricaoId(inscricao.id); const { data } = await api.get(`/inscricoes/${inscricao.id}/checklist`); setPessoas([{ id: "candidato", membroId: null, nome: data.candidato?.nome_completo || usuario?.nome_completo || "Titular", subtitulo: "Titular da inscrição", checklist: data.candidato?.checklist || [] }, ...(data.membros || []).map((membro) => ({ id: `membro-${membro.membro_id}`, membroId: membro.membro_id, nome: membro.nome_completo, subtitulo: "Familiar", checklist: membro.checklist || [] }))]); } catch (err) { setErro(err.response?.data?.detail || "Não foi possível carregar seus documentos."); } }, [usuario]);
  useEffect(() => { const timer = setTimeout(carregar, 0); return () => clearTimeout(timer); }, [carregar]);
  useEffect(() => { const timer = setInterval(carregar, 5000); return () => clearInterval(timer); }, [carregar]);
  async function enviarArquivo(file, pessoa, item) { if (!file || !inscricaoId) return; const chave = `${pessoa.id}-${item.solicitado_id}`; setEnviando(chave); setErro(""); try { const form = new FormData(); form.append("inscricao_id", inscricaoId); form.append("solicitado_id", item.solicitado_id); if (pessoa.membroId) form.append("membro_id", pessoa.membroId); form.append("file", file); await api.post("/documentos/upload", form); await carregar(); } catch (err) { setErro(err.response?.data?.detail || "Não foi possível enviar o documento."); } finally { setEnviando(""); } }
  return <main className="candidate-page"><CandidateTopbar title="Meus documentos" onLogout={onLogout}/><section className="candidate-dashboard"><header><div><p className="eyebrow">PAINEL DO CANDIDATO</p><h1>Olá, {usuario?.nome_completo?.split(" ")[0] || "candidato"}</h1><p>Veja as pendências e envie documentos sem sair desta página.</p></div></header>{erro && <div className="alert error-alert">{erro}</div>}<h2>Documentos por pessoa</h2><div className="person-cards">{pessoas.map((pessoa) => { const pendentes = pessoa.checklist.filter((item) => item.obrigatorio && !["ENVIADO", "ATENCAO"].includes(item.status)).length; const expandido = aberto === pessoa.id; return <article className="person-card" key={pessoa.id}><button className="person-card-head" onClick={() => setAberto(expandido ? "" : pessoa.id)}><span className="person-avatar">{pessoa.nome.charAt(0)}</span><span className="person-info"><strong>{pessoa.nome}</strong><small>{pessoa.subtitulo} · {pendentes ? `${pendentes} pendência${pendentes > 1 ? "s" : ""}` : "Documentação em dia"}</small></span><Badge resultado={pendentes ? "PENDENTE" : "ENVIADO"}/><ChevronDown className={expandido ? "chevron-open" : ""} size={19}/></button>{expandido && <div className="person-documents">{pessoa.checklist.length === 0 ? <p>Nenhum documento configurado para este edital.</p> : pessoa.checklist.flatMap((grupo) => grupo.itens.map((item) => { const chave = `${pessoa.id}-${item.solicitado_id}`; const pronto = ["ENVIADO", "ATENCAO"].includes(item.status); return <div className="person-document" key={chave}><FileText size={19}/><div><strong>{grupo.titulo}{item.rotulo ? ` — ${item.rotulo}` : ""}</strong><small>{item.mensagem_feedback || grupo.descricao || (pronto ? "Documento validado." : "Documento pendente.")}</small></div><Badge resultado={item.status}/><label className="inline-upload">{enviando === chave ? <Loader2 className="spin" size={16}/> : <FileUp size={16}/>}<span>{pronto ? "Substituir" : "Enviar"}</span><input type="file" accept=".pdf,image/png,image/jpeg" disabled={enviando === chave} onChange={(event) => enviarArquivo(event.target.files?.[0], pessoa, item)}/></label></div>; }))}</div>}</article>; })}</div></section></main>;
}

function DashboardEquipe({ usuario, onLogout }) {
  const navigate = useNavigate();
  const [busca, setBusca] = useState("");
  const [statusFiltro, setStatusFiltro] = useState("");
  const [candidatos, setCandidatos] = useState([]);
  const [metricas, setMetricas] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [atualizadoEm, setAtualizadoEm] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const [resumo, lista] = await Promise.all([
        api.get("/dashboard/metricas"),
        api.get("/inscricoes/dashboard/candidatos", { params: { busca, status_funil: statusFiltro || undefined, por_pagina: 100 } }),
      ]);
      setMetricas(resumo.data);
      setCandidatos(lista.data.itens || []);
      setAtualizadoEm(new Date());
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível carregar o painel gerencial.");
    } finally {
      setCarregando(false);
    }
  }, [busca, statusFiltro]);

  useEffect(() => { const timer = setTimeout(carregar, 250); return () => clearTimeout(timer); }, [carregar]);

  const dadosFunil = useMemo(() => Object.entries(metricas?.por_status || {}).map(([status, quantidade]) => ({ status, etapa: STATUS_LABELS[status] || status, quantidade, fill: STATUS_COLORS[status] || "#64748b" })), [metricas]);
  const dadosRosca = useMemo(() => dadosFunil.filter((item) => item.quantidade > 0), [dadosFunil]);
  const taxaConclusao = metricas?.total ? Math.round((metricas.concluidas / metricas.total) * 100) : 0;

  return <AnalystLayout onLogout={onLogout}><main className="dash-shell bi-shell"><section className="dash-card bi-card">
    <div className="dash-heading bi-heading"><div><p className="eyebrow">INTELIGÊNCIA OPERACIONAL</p><h1>Visão geral do processo seletivo</h1><p className="muted">Indicadores consolidados para acompanhar a jornada dos candidatos.</p></div><div className="bi-heading-actions"><span className="bi-updated"><Clock3 size={14}/> {atualizadoEm ? `Atualizado às ${atualizadoEm.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}` : "Carregando dados"}</span><button className="secondary-button" onClick={carregar} disabled={carregando}><RefreshCw className={carregando ? "spin" : ""} size={16}/> Atualizar</button>{usuario?.perfil === "ADMIN" && <button className="primary-button" onClick={() => navigate("/pre-cadastro")}><UserPlus size={16}/> Importar candidatos</button>}</div></div>

    {erro && <div className="alert error-alert">{erro}</div>}

    <div className="bi-kpi-grid">
      <KpiCard icon={UsersRound} label="Inscrições" value={metricas?.total} detail="Total no processo" tone="blue" onClick={() => setStatusFiltro("")}/>
      <KpiCard icon={AlertTriangle} label="Com dificuldade" value={metricas?.com_dificuldade} detail="Precisam de atenção" tone="amber" onClick={() => navigate("/fila-auditoria")}/>
      <KpiCard icon={FileText} label="Para auditoria" value={metricas?.prontas_auditoria} detail="Aguardando parecer" tone="rose" onClick={() => setStatusFiltro("PRONTO_AUDITORIA")}/>
      <KpiCard icon={CheckCircle2} label="Concluídas" value={metricas?.concluidas} detail={`${taxaConclusao}% de conclusão`} tone="green" onClick={() => setStatusFiltro("CONCLUIDO")}/>
    </div>

    <div className="bi-chart-grid">
      <article className="bi-panel bi-panel-wide"><header><div><p className="eyebrow">FUNIL</p><h2>Distribuição por etapa</h2></div><span>{metricas?.total || 0} inscrições</span></header><div className="bi-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={dadosRosca} layout="vertical" margin={{ top: 4, right: 24, left: 12, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e9eeeb"/><XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false}/><YAxis type="category" dataKey="etapa" width={128} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#526158" }}/><Tooltip cursor={{ fill: "#f3f7f4" }} formatter={(valor) => [`${valor} inscrição(ões)`, "Quantidade"]}/><Bar dataKey="quantidade" radius={[0, 6, 6, 0]}>{dadosRosca.map((item) => <Cell key={item.status} fill={item.fill}/>)}</Bar></BarChart></ResponsiveContainer></div></article>
      <article className="bi-panel"><header><div><p className="eyebrow">COMPOSIÇÃO</p><h2>Status das inscrições</h2></div></header><div className="bi-donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={dadosRosca} dataKey="quantidade" nameKey="etapa" innerRadius={62} outerRadius={90} paddingAngle={3}>{dadosRosca.map((item) => <Cell key={item.status} fill={item.fill}/>)}</Pie><Tooltip formatter={(valor) => [`${valor} inscrição(ões)`, "Quantidade"]}/><Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }}/></PieChart></ResponsiveContainer><div className="bi-donut-center"><strong>{taxaConclusao}%</strong><span>concluído</span></div></div></article>
    </div>

    <article className="bi-panel bi-table-panel"><header className="bi-table-header"><div><p className="eyebrow">DRILL-DOWN</p><h2>Acompanhamento por candidato</h2></div><div className="bi-filters"><label><Search size={16}/><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Buscar candidato ou inscrição"/></label><select value={statusFiltro} onChange={(event) => setStatusFiltro(event.target.value)}><option value="">Todas as etapas</option>{Object.entries(STATUS_LABELS).map(([status, label]) => <option key={status} value={status}>{label}</option>)}</select></div></header><div className="bi-table-wrap"><table className="history-table candidate-monitor"><thead><tr><th>Candidato</th><th>Etapa</th><th>Acesso</th><th>Dificuldade</th><th>Atividade</th><th></th></tr></thead><tbody>{carregando && candidatos.length === 0 ? <tr><td colSpan="6" className="bi-empty"><Loader2 className="spin" size={18}/> Carregando indicadores...</td></tr> : candidatos.length === 0 ? <tr><td colSpan="6" className="bi-empty">Nenhum candidato encontrado para os filtros selecionados.</td></tr> : candidatos.map((item) => <tr key={item.inscricao_id}><td><strong>{item.candidato}</strong><small>{item.email}</small></td><td><span className="bi-stage" style={{ "--stage-color": STATUS_COLORS[item.status_funil] }}>{STATUS_LABELS[item.status_funil] || item.status_funil}</span></td><td><Badge resultado={item.acessou ? "Acessou" : "Não acessou"}/></td><td><Badge resultado={item.com_dificuldade ? "Atenção" : "Sem alertas"}/></td><td><Badge resultado={item.ausente ? "Ausente" : "Ativo"}/></td><td><button className="row-action" onClick={() => navigate(`/detalhe/${item.inscricao_id}`)}>Analisar</button></td></tr>)}</tbody></table></div></article>
  </section></main></AnalystLayout>;
}

export default function Dashboard(props) { return props.usuario?.perfil === "CANDIDATO" ? <DashboardCandidato {...props}/> : <DashboardEquipe {...props}/>; }
