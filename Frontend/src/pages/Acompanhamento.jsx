import { Bell, Check, Circle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { CandidateTopbar } from "../components/PortalLayouts";

const etapas = ["Pré-cadastro", "KYC", "Grupo Familiar", "Comprovação Documental", "Auditoria", "Resultado Final"];
const nivel = { PRE_CADASTRADO: 0, KYC_PENDENTE: 1, KYC_VALIDADO: 2, FAMILIA_PENDENTE: 2, DOCS_PENDENTES: 3, PRONTO_AUDITORIA: 4, CONCLUIDO: 5 };
const textos = { PRE_CADASTRADO: "Envie sua identidade para iniciar.", KYC_PENDENTE: "Sua identidade está em validação.", FAMILIA_PENDENTE: "Informe ou confirme seu grupo familiar.", DOCS_PENDENTES: "Envie os documentos solicitados.", PRONTO_AUDITORIA: "Documentos enviados para auditoria.", CONCLUIDO: "Resultado final disponível." };

export default function Acompanhamento({ onLogout }) {
  const navigate = useNavigate(); const [jornada, setJornada] = useState(null); const [erro, setErro] = useState("");
  useEffect(() => { const timer = setTimeout(() => { api.get("/inscricoes/minha/jornada").then(({ data }) => setJornada(data)).catch((err) => setErro(err.response?.data?.detail || "Não foi possível carregar sua jornada.")); }, 0); return () => clearTimeout(timer); }, []);
  const atual = nivel[jornada?.status_funil] ?? 0;
  return <main className="candidate-page"><CandidateTopbar title="Acompanhamento" onLogout={onLogout}/><section className="journey-card"><p className="eyebrow">MINHA INSCRIÇÃO</p><h1>Acompanhe sua jornada</h1>{!jornada && !erro && <p className="kyc-processing"><Loader2 className="spin" size={17}/> Carregando andamento...</p>}{erro && <div className="alert error-alert">{erro}</div>}{jornada && <><div className="timeline">{etapas.map((etapa, i) => <div className={`timeline-step ${i < atual ? "done" : i === atual ? "current" : ""}`} key={etapa}><i>{i < atual ? <Check size={16}/> : <Circle size={15}/>}</i><div><strong>{etapa}</strong><p>{i < atual ? "Concluído" : i === atual ? textos[jornada.status_funil] || "Em andamento" : "Pendente"}</p></div></div>)}</div>{jornada.status_funil !== "CONCLUIDO" && jornada.status_funil !== "ABANDONO" && <button className="brand-button" onClick={() => navigate(jornada.proximo_destino)}>Continuar minha inscrição</button>}{jornada.status_funil === "CONCLUIDO" && <div className="success-alert"><strong>{jornada.status_geral}</strong><span>{jornada.parecer || "Sua inscrição foi analisada."}</span></div>}</>}<div className="journey-note"><Bell size={18}/> Você será avisado por e-mail quando uma etapa for atualizada.</div></section></main>;
}
