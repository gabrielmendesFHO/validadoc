import { AlertTriangle, ArrowUpRight, ChevronDown, ChevronLeft, ChevronRight, FileText, Loader2, Search, UsersRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import api from "../api/client";
import "./DashboardDrawer.css";

const CATEGORIAS = { RG: "RG · Frente", RG_VERSO: "RG · Verso", CNH: "CNH", RESIDENCIA: "Comprovante de residência", HOLERITE: "Holerite", OUTRO: "Outro documento" };
const STATUS_DOCUMENTOS = { CONCLUIDO: "Validado", ATENCAO: "Possível divergência", REJEITADO: "Recusado", ERRO_EXTRACAO: "Falha na leitura", PROCESSANDO_IA: "Em análise", PENDENTE: "Pendente" };

function statusDocumento(documento) {
  return documento.status === "CONCLUIDO" && documento.status_auditoria === "POSSIVEL_DIVERGENCIA" ? "ATENCAO" : documento.status;
}

function tomDocumento(status) {
  if (status === "CONCLUIDO") return "success";
  if (["REJEITADO", "ERRO_EXTRACAO"].includes(status)) return "danger";
  return "warning";
}

function ResumoInscricao({ inscricaoId, retorno, busca }) {
  const [consulta, setConsulta] = useState({ status: "loading" });
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api.get(`/dashboard/inscricoes/${inscricaoId}/resumo`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setConsulta({ status: "success", data }); })
      .catch((error) => { if (!controller.signal.aborted) setConsulta({ status: "error", error: error.response?.data?.detail || "Não foi possível carregar o resumo." }); });
    return () => controller.abort();
  }, [inscricaoId, tentativa]);

  if (consulta.status === "loading") return <p className="drill-state" role="status"><Loader2 className="spin" size={18}/> Carregando pessoas e documentos...</p>;
  if (consulta.status === "error") return <div className="drill-state" role="alert"><p>{consulta.error}</p><button className="secondary-button" onClick={() => { setConsulta({ status: "loading" }); setTentativa(valor => valor + 1); }}>Tentar carregar resumo</button></div>;
  const dados = consulta.data;
  const documentos = dados.pessoas.flatMap(pessoa => pessoa.documentos);
  const recusados = documentos.filter(documento => documento.status === "REJEITADO").length;
  const erros = documentos.filter(documento => documento.status === "ERRO_EXTRACAO").length;
  const faltantes = documentos.filter(documento => documento.obrigatorio && !documento.id).length;
  const divergencias = documentos.filter(documento => statusDocumento(documento) === "ATENCAO").length;
  const auditoriaUrl = `/auditoria/${inscricaoId}?retorno=${encodeURIComponent(retorno)}`;

  return <div className="drill-summary">
    <div className="drill-summary-counts" aria-label="Situação dos documentos">
      <span><strong>{recusados}</strong> {recusados === 1 ? "recusado" : "recusados"}</span>
      <span><strong>{erros}</strong> {erros === 1 ? "falha na leitura" : "falhas na leitura"}</span>
      <span><strong>{faltantes}</strong> {faltantes === 1 ? "obrigatório não enviado" : "obrigatórios não enviados"}</span>
      {divergencias > 0 && <span><strong>{divergencias}</strong> {divergencias === 1 ? "possível divergência" : "possíveis divergências"}</span>}
    </div>
    {dados.alertas_dificuldade > 0 && <p className="drill-notice"><AlertTriangle size={16}/><span>{dados.alertas_dificuldade} {dados.alertas_dificuldade === 1 ? "alerta registrado na inscrição" : "alertas registrados na inscrição"}. A causa desses alertas não foi detalhada no registro.</span></p>}
    {dados.pessoas.map(pessoa => <section className="drill-person" key={pessoa.membro_id ?? "titular"}>
      <header><span className="drill-avatar" aria-hidden="true">{pessoa.nome.charAt(0)}</span><div><h3>{pessoa.nome}</h3><small>{pessoa.tipo}</small></div></header>
      {pessoa.documentos.length === 0 ? <p className="drill-no-docs">Nenhum documento solicitado neste edital.</p> : <ul className="drill-documents">{pessoa.documentos.map(documento => {
        const categoria = CATEGORIAS[documento.categoria] || documento.categoria;
        const status = statusDocumento(documento);
        const problema = ["REJEITADO", "ERRO_EXTRACAO", "ATENCAO"].includes(status);
        return <li key={documento.solicitado_id} className={`drill-document ${problema ? "has-issue" : ""}`}>
          <div className="drill-document-heading"><FileText size={17}/><strong>{categoria}</strong><span className={`drill-badge ${tomDocumento(status)}`}>{!documento.id ? "Não enviado" : STATUS_DOCUMENTOS[status] || status}</span></div>
          <p>{documento.motivo || (problema ? "Motivo não informado." : !documento.id ? (documento.obrigatorio ? "Envio obrigatório pendente." : "Envio opcional.") : documento.status === "CONCLUIDO" ? "Documento validado." : "Aguarde a conclusão da análise.")}</p>
          {documento.id && <Link className="drill-document-link" to={`${auditoriaUrl}&documento=${documento.id}`} state={{ resumoBusca: busca }} aria-label={`Abrir ${categoria} de ${pessoa.nome}`}>Abrir documento <ArrowUpRight size={14}/></Link>}
        </li>;
      })}</ul>}
    </section>)}
    <Link className="drill-audit-link" to={auditoriaUrl} state={{ resumoBusca: busca }}>Analisar inscrição completa <ArrowUpRight size={16}/></Link>
  </div>;
}

function numeroPositivo(valor) {
  const numero = Number(valor);
  return Number.isSafeInteger(numero) && numero > 0 ? numero : 1;
}

export default function DashboardDrawer({ selecao, rotulosStatus, onClose }) {
  const dialogRef = useRef(null);
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const filtroInicialRef = useRef(params.get("resumo"));
  const focoInicialRef = useRef(null);
  // O texto pesquisado fica no histórico privado da aba, fora do endereço.
  const busca = typeof location.state?.resumoBusca === "string" ? location.state.resumoBusca.slice(0, 100) : "";
  const pagina = numeroPositivo(params.get("resumo_pagina"));
  const expandida = params.get("inscricao");
  const [tentativa, setTentativa] = useState(0);
  const [consulta, setConsulta] = useState(null);
  const chave = JSON.stringify([selecao.status, selecao.dificuldade, busca, pagina, tentativa]);
  const dados = consulta?.chave === chave && consulta.status === "success" ? consulta.data : null;
  const erro = consulta?.chave === chave && consulta.status === "error" ? consulta.error : null;
  const carregando = !dados && !erro;
  const retornoParams = new URLSearchParams({ resumo: params.get("resumo") });
  if (pagina > 1) retornoParams.set("resumo_pagina", String(pagina));
  if (expandida && /^\d+$/.test(expandida)) retornoParams.set("inscricao", expandida);
  const retorno = `/dashboard?${retornoParams.toString()}`;

  useEffect(() => {
    const dialog = dialogRef.current;
    const overflowAnterior = document.body.style.overflow;
    if (focoInicialRef.current === null) focoInicialRef.current = { elemento: document.activeElement };
    const focoAnterior = focoInicialRef.current.elemento;
    const filtroInicial = filtroInicialRef.current;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog.close();
      document.body.style.overflow = overflowAnterior;
      const destino = focoAnterior !== document.body && focoAnterior?.isConnected && !dialog.contains(focoAnterior) ? focoAnterior
        : document.querySelector(`[data-resumo="${filtroInicial}"]`) || document.querySelector(".bi-kpi");
      if (destino?.isConnected) destino.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api.get("/inscricoes/dashboard/candidatos", { signal: controller.signal, params: {
        busca, pagina, por_pagina: 20, status_funil: selecao.status || undefined,
        com_dificuldade: selecao.dificuldade ? true : undefined,
      } }).then(({ data }) => { if (!controller.signal.aborted) setConsulta({ chave, status: "success", data }); })
        .catch((error) => { if (!controller.signal.aborted) setConsulta({ chave, status: "error", error: error.response?.data?.detail || "Não foi possível carregar as inscrições." }); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [busca, pagina, selecao.status, selecao.dificuldade, chave]);

  function atualizar(alteracoes) {
    const novaBusca = Object.hasOwn(alteracoes, "resumo_busca") ? alteracoes.resumo_busca || "" : busca;
    setParams(anteriores => {
      const proximos = new URLSearchParams(anteriores);
      proximos.delete("resumo_busca");
      for (const [campo, valor] of Object.entries(alteracoes)) {
        if (campo === "resumo_busca") continue;
        if (valor === null || valor === "") proximos.delete(campo);
        else proximos.set(campo, String(valor));
      }
      return proximos;
    }, { replace: true, state: { resumoBusca: novaBusca } });
  }

  const inicio = dados?.itens.length ? (pagina - 1) * dados.por_pagina + 1 : 0;
  const fim = dados?.itens.length ? inicio + dados.itens.length - 1 : 0;
  return <dialog ref={dialogRef} className="dashboard-drawer" aria-labelledby="drill-title" aria-describedby="drill-description" onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => {
    if (event.target === event.currentTarget && event.clientX < event.currentTarget.getBoundingClientRect().left) onClose();
  }}>
    <header className="drill-header"><div><p className="eyebrow">VISÃO DETALHADA</p><h2 id="drill-title">{selecao.titulo}</h2><p id="drill-description">{selecao.descricao}</p></div><button className="drill-close" type="button" onClick={onClose} aria-label="Fechar resumo" autoFocus><X size={20}/></button></header>
    <div className="drill-toolbar"><div className="drill-total" role="status"><UsersRound size={17}/><strong>{dados ? dados.total : "—"}</strong><span>{dados?.total === 1 ? "inscrição" : "inscrições"}{busca ? " na busca" : ""}</span></div><label className="drill-search"><Search size={17}/><input aria-label="Buscar no resumo" placeholder="Buscar nome ou nº da inscrição" maxLength={100} value={busca} onChange={event => atualizar({ resumo_busca: event.target.value, resumo_pagina: null, inscricao: null })}/></label><p>Expanda uma inscrição para ver pessoas e documentos.</p></div>
    <div className="drill-content" aria-busy={carregando}>
      {carregando ? <p className="drill-state" role="status"><Loader2 className="spin" size={20}/> Carregando inscrições...</p> : erro ? <div className="drill-state" role="alert"><AlertTriangle size={22}/><p>{erro}</p><button className="secondary-button" onClick={() => setTentativa(valor => valor + 1)}>Tentar novamente</button></div> : dados.itens.length === 0 ? <div className="drill-state"><UsersRound size={26}/><p>Nenhuma inscrição encontrada.</p>{busca && <button className="secondary-button" onClick={() => atualizar({ resumo_busca: null, resumo_pagina: null, inscricao: null })}>Limpar busca</button>}{pagina > 1 && <button className="secondary-button" onClick={() => atualizar({ resumo_pagina: null, inscricao: null })}>Voltar à primeira página</button>}</div> : <ul className="drill-enrollments">{dados.itens.map(item => {
        const aberta = expandida === String(item.inscricao_id);
        return <li className={`drill-enrollment ${aberta ? "is-open" : ""}`} key={item.inscricao_id}>
          <button type="button" className="drill-enrollment-toggle" aria-label={`Ver resumo de ${item.candidato}`} aria-expanded={aberta} aria-controls={`resumo-inscricao-${item.inscricao_id}`} onClick={() => atualizar({ inscricao: aberta ? null : item.inscricao_id })}>
            <span className="drill-enrollment-copy"><small>INSCRIÇÃO #{item.inscricao_id}</small><strong>{item.candidato}</strong><span>{rotulosStatus[item.status_funil] || item.status_funil}</span></span><span className={`drill-badge ${item.com_dificuldade ? "danger" : "neutral"}`}>{item.com_dificuldade ? "Requer atenção" : "Sem alertas"}</span><ChevronDown className={aberta ? "is-expanded" : ""} size={19}/>
          </button>
          {aberta && <div id={`resumo-inscricao-${item.inscricao_id}`}><ResumoInscricao inscricaoId={item.inscricao_id} retorno={retorno} busca={busca}/></div>}
        </li>;
      })}</ul>}
    </div>
    {dados && <footer className="drill-pagination"><span>{inicio}–{fim} de {dados.total}</span><div><button type="button" aria-label="Página anterior do resumo" disabled={pagina === 1} onClick={() => atualizar({ resumo_pagina: pagina - 1, inscricao: null })}><ChevronLeft size={17}/></button><span>Página {pagina}</span><button type="button" aria-label="Próxima página do resumo" disabled={fim >= dados.total} onClick={() => atualizar({ resumo_pagina: pagina + 1, inscricao: null })}><ChevronRight size={17}/></button></div></footer>}
  </dialog>;
}
