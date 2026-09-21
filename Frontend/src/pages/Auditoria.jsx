import { AlertTriangle, ArrowLeft, CheckCircle2, FileSearch, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/client";
import { AnalystLayout } from "../components/PortalLayouts";

function formatarValor(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "boolean") return valor ? "Sim" : "Não";
  if (typeof valor === "object") return JSON.stringify(valor);
  return String(valor);
}

export default function Auditoria({ onLogout }) {
  const { inscricaoId } = useParams();
  const navigate = useNavigate();
  const [dados, setDados] = useState(null);
  const [documentoAtivo, setDocumentoAtivo] = useState(null);
  const [arquivoUrl, setArquivoUrl] = useState("");
  const [decisao, setDecisao] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [concluido, setConcluido] = useState(null);

  useEffect(() => {
    let ativo = true;
    api.get(`/auditoria/${inscricaoId}`)
      .then(({ data }) => {
        if (!ativo) return;
        setDados(data);
        setDocumentoAtivo(data.documentos[0] || null);
        setJustificativa(data.inscricao.parecer || "");
      })
      .catch((error) => { if (ativo) setErro(error.response?.data?.detail || "Não foi possível carregar a auditoria."); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [inscricaoId]);

  useEffect(() => {
    if (!documentoAtivo) return undefined;
    let urlTemporaria = "";
    let ativo = true;
    api.get(documentoAtivo.arquivo_url, { responseType: "blob" })
      .then(({ data }) => {
        if (!ativo) return;
        urlTemporaria = URL.createObjectURL(data);
        setArquivoUrl(urlTemporaria);
      })
      .catch(() => { if (ativo) setArquivoUrl(""); });
    return () => { ativo = false; if (urlTemporaria) URL.revokeObjectURL(urlTemporaria); };
  }, [documentoAtivo]);

  async function enviarParecer(event) {
    event.preventDefault();
    if (!decisao || justificativa.trim().length < 3) return;
    setSalvando(true); setErro("");
    try {
      const { data } = await api.put(`/auditoria/${inscricaoId}/parecer`, { decisao, justificativa });
      setConcluido(data);
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível salvar o parecer.");
    } finally {
      setSalvando(false);
    }
  }

  return <AnalystLayout onLogout={onLogout}><div className="analyst-page audit-page">
    <button className="back-button" onClick={() => navigate("/fila-auditoria")}><ArrowLeft size={16}/> Voltar para a fila</button>
    <header><div><p className="eyebrow">INSCRIÇÃO #{inscricaoId}</p><h1>Auditoria documental</h1><p className="muted">Compare o documento com os dados declarados antes de emitir o parecer.</p></div>{dados && <span className="status-chip">{dados.inscricao.status_funil.replaceAll("_", " ")}</span>}</header>
    {carregando && <div className="panel loading-state"><Loader2 className="spin" size={18}/> Carregando documentos...</div>}
    {erro && <div className="alert error-alert"><AlertTriangle size={18}/> {erro}</div>}
    {dados && <>
      <div className="audit-document-tabs">{dados.documentos.map((documento) => <button key={documento.id} className={documentoAtivo?.id === documento.id ? "active" : ""} onClick={() => setDocumentoAtivo(documento)}><FileSearch size={16}/><span>{documento.categoria}<small>{documento.pessoa}</small></span></button>)}{dados.documentos.length === 0 && <p>Nenhum documento enviado.</p>}</div>
      <section className="audit-split-view">
        <article className="audit-preview-panel"><div className="audit-panel-heading"><div><span>Documento original</span><strong>{documentoAtivo?.nome_arquivo || "Nenhum arquivo selecionado"}</strong></div>{documentoAtivo && <span className="table-badge">{documentoAtivo.status_processamento}</span>}</div><div className="audit-preview">{!documentoAtivo ? <p>Selecione um documento.</p> : !arquivoUrl ? <Loader2 className="spin"/> : documentoAtivo.mime_type === "application/pdf" ? <object data={arquivoUrl} type="application/pdf" aria-label={documentoAtivo.nome_arquivo}/> : <img src={arquivoUrl} alt={documentoAtivo.nome_arquivo || "Documento enviado"}/>}</div></article>
        <article className="audit-data-panel"><div className="audit-panel-heading"><div><span>Dados cruzados</span><strong>{documentoAtivo?.categoria || "Documento"}</strong></div></div><h3>Dados declarados</h3><dl className="audit-data-list"><div><dt>Nome</dt><dd>{documentoAtivo?.membro_id ? documentoAtivo.pessoa : dados.candidato.nome_completo}</dd></div><div><dt>CPF</dt><dd>{documentoAtivo?.membro_id ? dados.membros.find((membro) => membro.id === documentoAtivo.membro_id)?.cpf || "—" : dados.candidato.cpf || "—"}</dd></div></dl><h3>Dados extraídos pela IA</h3>{documentoAtivo?.dados_extraidos ? <dl className="audit-data-list">{Object.entries(documentoAtivo.dados_extraidos).map(([campo, valor]) => <div key={campo}><dt>{campo.replaceAll("_", " ")}</dt><dd>{formatarValor(valor)}</dd></div>)}</dl> : <p className="muted">Sem dados extraídos para este documento.</p>}{documentoAtivo?.parecer_ia && <div className={`alert ${documentoAtivo.status_auditoria === "POSSIVEL_DIVERGENCIA" ? "error-alert" : "success-alert"}`}>{documentoAtivo.parecer_ia}</div>}</article>
      </section>
      <form className="manual-decision" onSubmit={enviarParecer}><div><p className="eyebrow">PARECER FINAL</p><h2>Decisão do analista</h2><p className="muted">A decisão conclui a inscrição e fica disponível para o candidato.</p></div><div className="decision-buttons"><button type="button" className={decisao === "APROVAR" ? "selected approve" : "approve"} onClick={() => setDecisao("APROVAR")}><CheckCircle2 size={18}/> Aprovar</button><button type="button" className={decisao === "REJEITAR" ? "selected reject" : "reject"} onClick={() => setDecisao("REJEITAR")}><XCircle size={18}/> Rejeitar</button></div><label>Justificativa<textarea value={justificativa} onChange={(event) => setJustificativa(event.target.value)} placeholder="Explique os critérios considerados no parecer..." rows="4" required minLength="3"/></label><button className="brand-button" disabled={salvando || !decisao || justificativa.trim().length < 3}>{salvando && <Loader2 className="spin" size={17}/>} Salvar parecer</button>{concluido && <div className="alert success-alert"><CheckCircle2 size={18}/><span>Parecer salvo. Resultado: <strong>{concluido.status_geral}</strong>.</span></div>}</form>
    </>}
  </div></AnalystLayout>;
}
