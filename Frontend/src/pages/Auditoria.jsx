import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronDown, ExternalLink, FileSearch, Loader2, ScanLine, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/client";
import { AnalystLayout } from "../components/PortalLayouts";
import "./Auditoria.css";

function formatarValor(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "boolean") return valor ? "Sim" : "Não";
  if (typeof valor === "object") return JSON.stringify(valor);
  return String(valor);
}

const rotulosStatus = {
  PRONTO_AUDITORIA: "Aguardando analista", REVISAO_MANUAL: "Revisão manual",
  CONCLUIDO: "Concluído", PROCESSANDO_IA: "Em processamento", REJEITADO: "Rejeitado",
  ERRO_EXTRACAO: "Erro na extração", PENDENTE: "Pendente", APTO: "Apto", NAO_APTO: "Não apto",
};
const categorias = { RG: "RG · Frente", RG_VERSO: "RG · Verso", CNH: "CNH", RESIDENCIA: "Residência", HOLERITE: "Holerite" };
function rotuloStatus(status) { return rotulosStatus[status] || status?.replaceAll("_", " ") || "Não realizada"; }
function tomStatus(status) {
  if (["CONCLUIDO", "APTO"].includes(status)) return "success";
  if (["REJEITADO", "ERRO_EXTRACAO", "NAO_APTO"].includes(status)) return "danger";
  return "warning";
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
  const [conferindo, setConferindo] = useState(false);
  const [erroArquivo, setErroArquivo] = useState(false);

  function selecionarDocumento(documento) {
    if (documentoAtivo?.id === documento.id) return;
    setArquivoUrl("");
    setErroArquivo(false);
    setDocumentoAtivo(documento);
  }

  async function conferirDocumentos() {
    setConferindo(true); setErro("");
    try {
      await api.post(`/inscricoes/${inscricaoId}/auditar`);
      const { data } = await api.get(`/auditoria/${inscricaoId}`);
      setDados(data);
      setJustificativa(data.inscricao.parecer || "");
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível conferir os documentos.");
    } finally { setConferindo(false); }
  }

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
      .catch(() => { if (ativo) { setArquivoUrl(""); setErroArquivo(true); } });
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

  const inconsistencias = dados?.inscricao.inconsistencias || [];
  return <AnalystLayout onLogout={onLogout}>
    <div className="analyst-page audit-page">
      <button className="back-button" onClick={() => navigate("/fila-auditoria")}><ArrowLeft size={16}/> Voltar para a fila</button>
      <header className="audit-page-header">
        <div><p className="eyebrow">INSCRIÇÃO #{inscricaoId}</p><h1>Auditoria documental</h1><p className="muted">Confira os documentos e os dados antes de emitir o parecer.</p></div>
        {dados && <span className={`audit-badge ${tomStatus(dados.inscricao.status_funil)}`}><span/>{rotuloStatus(dados.inscricao.status_funil)}</span>}
      </header>
      {carregando && <div className="panel loading-state"><Loader2 className="spin" size={18}/> Carregando documentos...</div>}
      {erro && <div className="alert error-alert" role="alert"><AlertTriangle size={18}/> {erro}</div>}
      {dados && <>
        <section className="audit-overview" aria-label="Resumo da inscrição">
          <div className="audit-candidate"><span className="audit-avatar"><ShieldCheck size={23}/></span><div><span>Candidato</span><strong>{dados.candidato.nome_completo || "Nome não informado"}</strong></div></div>
          <div className="audit-metric"><span>Documentos enviados</span><strong>{dados.documentos.length}<small> envios</small></strong></div>
          <div className="audit-metric"><span>Conferência automática</span><strong className={`audit-result ${tomStatus(dados.inscricao.status_geral)}`}>{rotuloStatus(dados.inscricao.status_geral)}</strong></div>
        </section>

        <section className="audit-check-card" aria-label="Conferência automática">
          <div className="audit-check-header"><div className="audit-section-title"><span className="audit-section-icon"><ScanLine size={20}/></span><div><h2>Conferência automática</h2><p>Consulte o resultado e os pontos que precisam de atenção.</p></div></div>
            <button className="secondary-button" disabled={conferindo || salvando} onClick={conferirDocumentos}>{conferindo ? <Loader2 className="spin" size={16}/> : <ScanLine size={16}/>} {conferindo ? "Conferindo documentos..." : "Executar conferência automática"}</button>
          </div>
          {inconsistencias.length > 0 ? <details className="audit-findings"><summary><AlertTriangle size={17}/><strong>{inconsistencias.length} {inconsistencias.length === 1 ? "ponto precisa" : "pontos precisam"} de atenção</strong><span>Ver detalhes</span><ChevronDown size={16}/></summary><ul>{inconsistencias.map((item,index) => <li key={index}>{item}</li>)}</ul></details> : <p className="audit-check-note">{dados.inscricao.parecer || "Execute a conferência para verificar os documentos enviados."}</p>}
        </section>

        <div className="audit-workspace">
          <aside className="audit-document-picker" aria-label="Documentos enviados"><div className="audit-picker-heading"><h2>Documentos</h2><span>{dados.documentos.length}</span></div>
            <div className="audit-document-list">{dados.documentos.map((documento) => <button key={documento.id} aria-pressed={documentoAtivo?.id === documento.id} className={`audit-document-option ${documentoAtivo?.id === documento.id ? "active" : ""}`} onClick={() => selecionarDocumento(documento)}>
              <span className="audit-document-type"><FileSearch size={17}/><strong>{categorias[documento.categoria] || documento.categoria}</strong><small>#{documento.id}</small></span>
              <span className="audit-document-person">{documento.pessoa}</span><span className="audit-document-file" title={documento.nome_arquivo}>{documento.nome_arquivo}</span>
              <span className={`audit-document-status ${tomStatus(documento.status_processamento)}`}><span/>{rotuloStatus(documento.status_processamento)}</span>
            </button>)}{dados.documentos.length === 0 && <p className="audit-empty">Nenhum documento enviado.</p>}</div>
          </aside>
          <section className="audit-split-view" aria-label="Comparação documental">
            <article className="audit-preview-panel"><div className="audit-panel-heading"><div><span>Documento original</span><strong title={documentoAtivo?.nome_arquivo}>{documentoAtivo?.nome_arquivo || "Nenhum arquivo selecionado"}</strong></div>{arquivoUrl && <a className="audit-open-file" href={arquivoUrl} target="_blank" rel="noreferrer" aria-label="Abrir documento original em nova aba" title="Abrir original"><ExternalLink size={17}/></a>}</div>
              <div className="audit-preview">{!documentoAtivo ? <div className="audit-preview-empty"><FileSearch size={32}/><p>Selecione um documento para conferir.</p></div> : erroArquivo ? <div className="audit-preview-empty" role="alert"><AlertTriangle size={28}/><p>Não foi possível abrir o arquivo. Selecione outro documento ou recarregue a página.</p></div> : !arquivoUrl ? <div className="audit-preview-empty" role="status"><Loader2 className="spin" size={24}/><p>Carregando documento...</p></div> : documentoAtivo.mime_type === "application/pdf" ? <object data={arquivoUrl} type="application/pdf" aria-label={documentoAtivo.nome_arquivo}><a href={arquivoUrl} target="_blank" rel="noreferrer">Abrir PDF em nova aba</a></object> : <img src={arquivoUrl} alt={documentoAtivo.nome_arquivo || "Documento enviado"}/>}</div>
            </article>
            <article className="audit-data-panel"><div className="audit-panel-heading"><div><span>Comparação de dados</span><strong>{categorias[documentoAtivo?.categoria] || documentoAtivo?.categoria || "Documento"}</strong></div>{documentoAtivo && <span className={`audit-badge ${tomStatus(documentoAtivo.status_processamento)}`}>{rotuloStatus(documentoAtivo.status_processamento)}</span>}</div>
              {documentoAtivo ? <div className="audit-data-body"><h3>Dados declarados <span>Cadastro</span></h3><dl className="audit-data-list"><div><dt>Nome</dt><dd>{documentoAtivo.membro_id ? documentoAtivo.pessoa : dados.candidato.nome_completo}</dd></div><div><dt>CPF</dt><dd>{documentoAtivo.membro_id ? dados.membros.find((membro) => membro.id === documentoAtivo.membro_id)?.cpf || "—" : dados.candidato.cpf || "—"}</dd></div></dl>
                <h3>Dados extraídos <span>Inteligência artificial</span></h3>{documentoAtivo.dados_extraidos ? <dl className="audit-data-list">{Object.entries(documentoAtivo.dados_extraidos).map(([campo, valor]) => <div key={campo}><dt>{campo === "cpf" ? "CPF" : campo.replaceAll("_", " ")}</dt><dd>{formatarValor(valor)}</dd></div>)}</dl> : <p className="muted">Sem dados extraídos para este documento.</p>}
                {documentoAtivo.parecer_ia && <div className={`audit-document-note ${documentoAtivo.status_auditoria === "POSSIVEL_DIVERGENCIA" || documentoAtivo.status_processamento !== "CONCLUIDO" ? "warning" : "success"}`}><strong>Resultado da leitura</strong><p>{documentoAtivo.parecer_ia}</p></div>}
              </div> : <p className="audit-empty">Os dados aparecerão ao selecionar um documento.</p>}
            </article>
          </section>
        </div>

        <form className="manual-decision audit-decision-card" onSubmit={enviarParecer}>
          <div className="audit-decision-heading"><span className="audit-section-icon"><ShieldCheck size={22}/></span><div><p className="eyebrow">PARECER FINAL</p><h2>Decisão do analista</h2><p className="muted">A decisão conclui a inscrição e fica disponível para o candidato.</p></div></div>
          <div className="audit-decision-fields"><fieldset><legend>Selecione a decisão</legend><div className="decision-buttons"><button type="button" aria-pressed={decisao === "APROVAR"} className={decisao === "APROVAR" ? "selected approve" : "approve"} onClick={() => setDecisao("APROVAR")}><CheckCircle2 size={18}/> Aprovar</button><button type="button" aria-pressed={decisao === "REJEITAR"} className={decisao === "REJEITAR" ? "selected reject" : "reject"} onClick={() => setDecisao("REJEITAR")}><XCircle size={18}/> Rejeitar</button></div></fieldset>
            <label>Justificativa<textarea value={justificativa} onChange={(event) => setJustificativa(event.target.value)} placeholder="Explique os critérios considerados no parecer..." rows="4" required minLength="3"/><small>Descreva os documentos e critérios que sustentam a decisão.</small></label>
          </div>
          <div className="audit-decision-footer"><span>{decisao ? `Decisão selecionada: ${decisao === "APROVAR" ? "aprovar" : "rejeitar"}` : "Selecione uma decisão e confira a justificativa para salvar."}</span><button className="brand-button" disabled={salvando || !decisao || justificativa.trim().length < 3}>{salvando ? <Loader2 className="spin" size={17}/> : <ShieldCheck size={17}/>} Salvar parecer</button></div>
          {concluido && <div className="alert success-alert" role="status"><CheckCircle2 size={18}/><span>Parecer salvo. Resultado: <strong>{rotuloStatus(concluido.status_geral)}</strong>.</span></div>}
        </form>
      </>}
    </div>
  </AnalystLayout>;
}
