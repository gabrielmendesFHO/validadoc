import { CheckCircle2, FileUp, Info, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { CandidateTopbar } from "../components/PortalLayouts";

export default function KYC({ onLogout }) {
  const input = useRef(); const navigate = useNavigate();
  const [arquivo, setArquivo] = useState(null); const [inscricaoId, setInscricaoId] = useState(null);
  const [solicitado, setSolicitado] = useState(null); const [status, setStatus] = useState("PRE_CADASTRADO");
  const [documentoConcluido, setDocumentoConcluido] = useState(false);
  const [statusDocumento, setStatusDocumento] = useState("PENDENTE");
  const [enviando, setEnviando] = useState(false); const [erro, setErro] = useState("");

  async function carregar() {
    try {
      const { data: inscricao } = await api.get("/inscricoes/minha"); setInscricaoId(inscricao.id);
      const { data } = await api.get(`/inscricoes/${inscricao.id}/kyc`); setStatus(data.status_funil); setDocumentoConcluido(data.documentos.some((doc) => doc.status === "CONCLUIDO"));
      const documentoAtual = data.documentos.find((doc) => doc.status !== "PENDENTE") || null;
      setStatusDocumento(documentoAtual?.status || "PENDENTE");
      if (["REJEITADO", "ERRO_EXTRACAO"].includes(documentoAtual?.status)) setErro(documentoAtual.mensagem || "Não foi possível validar o documento. Envie uma nova versão.");
      setSolicitado(data.documentos.find((doc) => doc.nome_documento === "CNH") || data.documentos.find((doc) => doc.nome_documento === "RG") || null);
    } catch (err) { setErro(err.response?.data?.detail || "Não foi possível preparar a validação de identidade."); }
  }
  useEffect(() => { const timer = setTimeout(carregar, 0); return () => clearTimeout(timer); }, []);
  useEffect(() => { if (statusDocumento !== "PROCESSANDO_IA") return undefined; const timer = setInterval(carregar, 3000); return () => clearInterval(timer); }, [statusDocumento]);
  useEffect(() => {
    const destinos = { FAMILIA_PENDENTE: "/familia", DOCS_PENDENTES: "/upload", PRONTO_AUDITORIA: "/acompanhamento", CONCLUIDO: "/acompanhamento", ABANDONO: "/acompanhamento" };
    if (destinos[status]) navigate(destinos[status], { replace: true });
  }, [status, navigate]);

  async function enviar() {
    if (!arquivo || !solicitado || !inscricaoId) return; setEnviando(true); setErro("");
    try { const form = new FormData(); form.append("inscricao_id", inscricaoId); form.append("solicitado_id", solicitado.solicitado_id); form.append("file", arquivo); await api.post("/documentos/upload", form); setArquivo(null); await carregar(); }
    catch (err) { setErro(err.response?.data?.detail || "Não foi possível enviar o documento."); }
    finally { setEnviando(false); }
  }
  async function continuar() {
    try { await api.post(`/inscricoes/${inscricaoId}/kyc/concluir`); navigate("/familia", { replace: true }); }
    catch (err) { setErro(err.response?.data?.detail || "A validação ainda não foi concluída."); }
  }
  const etapaConcluida = status === "FAMILIA_PENDENTE" || status === "KYC_VALIDADO";
  const prontoParaContinuar = documentoConcluido && !etapaConcluida;
  const processando = statusDocumento === "PROCESSANDO_IA";
  return <main className="candidate-page"><CandidateTopbar title="Sua inscrição" onLogout={onLogout}/><section className="kyc-card"><div className="kyc-heading"><div className="round-icon"><LockKeyhole/></div><div><span className="required-badge">ETAPA OBRIGATÓRIA</span><h1>Validação de Identidade (KYC)</h1><p>Envie um documento oficial para confirmar sua identidade.</p></div></div><div className="kyc-body"><button className="upload-dropzone" disabled={enviando || etapaConcluida || processando} onClick={() => input.current?.click()}><FileUp size={36}/><strong>{arquivo?.name || (processando ? "Documento em validação" : "Arraste seu RG ou CNH aqui")}</strong><span>Formatos aceitos: PDF, JPG ou PNG</span><em>{processando ? "Aguarde" : "Selecionar arquivo"}</em></button><input ref={input} hidden type="file" accept=".pdf,image/png,image/jpeg" onChange={(e) => setArquivo(e.target.files?.[0])}/><div className="document-example">{(etapaConcluida || prontoParaContinuar) ? <CheckCircle2 size={64}/> : <ShieldCheck size={64}/>}<strong>{(etapaConcluida || prontoParaContinuar) ? "Identidade validada" : "Documento oficial"}</strong><span>RG ou CNH legível, frente e verso quando necessário.</span></div></div>{erro && <div className="alert error-alert">{erro}</div>}{arquivo && <button className="brand-button" disabled={enviando} onClick={enviar}>{enviando && <Loader2 className="spin" size={17}/>} Validar documento</button>}{processando && <p className="kyc-processing"><Loader2 className="spin" size={17}/> Estamos validando seu documento. Você será direcionado ao grupo familiar assim que terminar.</p>}{prontoParaContinuar && <button className="brand-button" onClick={continuar}>Continuar para Grupo Familiar</button>}<div className="kyc-notice"><Info size={19}/><span>Seus dados são criptografados e usados exclusivamente para validação da inscrição.</span></div></section></main>;
}
