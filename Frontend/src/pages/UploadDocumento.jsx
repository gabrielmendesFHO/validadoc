import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  Clock,
  FileText,
  FileUp,
  Loader2,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

// ─────────────────────────────────────────────
// Sub-componentes de UI
// ─────────────────────────────────────────────

function FeedbackBox({ nivel, mensagem }) {
  if (!mensagem) return null;
  const cfg = {
    erro: { bg: "#fef2f2", border: "#fecaca", text: "#b91c1c", icon: <XCircle size={15} style={{ flexShrink: 0, marginTop: 2 }} />, titulo: "Documento rejeitado" },
    aviso: { bg: "#fffbeb", border: "#fde68a", text: "#92400e", icon: <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />, titulo: "Atenção" },
    sucesso: { bg: "#ecfdf5", border: "#a7f3d0", text: "#065f46", icon: <CheckCircle2 size={15} style={{ flexShrink: 0, marginTop: 2 }} />, titulo: "Aprovado" },
  }[nivel] || { bg: "#f9fafb", border: "#e5e7eb", text: "#374151", icon: null, titulo: "Aviso" };

  return (
    <div style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.text, borderRadius: 8, padding: "10px 12px", fontSize: 13, marginTop: 10, display: "flex", alignItems: "flex-start", gap: 8, lineHeight: 1.5 }}>
      {cfg.icon}
      <div><strong>{cfg.titulo}: </strong>{mensagem}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const MAP = {
    ENVIADO:       { cor: "#10b981", icon: <CheckCircle2 size={14} />, txt: "Enviado" },
    ATENCAO:       { cor: "#d97706", icon: <AlertTriangle size={14} />, txt: "Atenção" },
    REJEITADO:     { cor: "#ef4444", icon: <XCircle size={14} />, txt: "Rejeitado" },
    ERRO:          { cor: "#ef4444", icon: <XCircle size={14} />, txt: "Erro de extração" },
    PROCESSANDO:   { cor: "#6366f1", icon: <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />, txt: "Analisando…" },
  };
  const s = MAP[status] || { cor: "#9ca3af", icon: <Clock size={14} />, txt: "Pendente" };
  return (
    <span style={{ fontSize: 13, fontWeight: 600, color: s.cor, display: "inline-flex", alignItems: "center", gap: 4 }}>
      {s.icon} {s.txt}
    </span>
  );
}

/** Spinner animado mostrado enquanto o card está aguardando a IA */
function ProcessingOverlay() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "20px 16px", background: "#f5f3ff", borderRadius: 10, border: "1px solid #ddd6fe", marginTop: 10 }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <Loader2 size={20} color="#6366f1" style={{ animation: "spin 1s linear infinite" }} />
        <span style={{ fontSize: 14, fontWeight: 600, color: "#4338ca" }}>Analisando com IA…</span>
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {[0, 1, 2].map((i) => (
          <span key={i} style={{
            width: 8, height: 8, borderRadius: "50%", background: "#818cf8",
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
      <p style={{ fontSize: 12, color: "#6b7280", margin: 0, textAlign: "center" }}>
        Verificando legibilidade, autenticidade e dados do documento…
      </p>
    </div>
  );
}

// CSS keyframes injetados uma única vez
const STYLE_TAG = `
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.1); } }
`;
if (!document.getElementById("upload-animations")) {
  const s = document.createElement("style");
  s.id = "upload-animations";
  s.textContent = STYLE_TAG;
  document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// Componente principal
// ─────────────────────────────────────────────

const POLL_INTERVAL_MS = 3000; // consultar status a cada 3 s

export default function UploadDocumento({ usuario }) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [arquivosSelecionados, setArquivosSelecionados] = useState({});
  const [enviando, setEnviando] = useState(false);
  // Mapa documentoId → true para os docs que ainda estão "PROCESSANDO_IA"
  const [processando, setProcessando] = useState({});
  const inputRefs = useRef({});
  const pollTimerRef = useRef(null);

  // ── carrega / recarrega checklist ──────────
  const carregarChecklist = useCallback(async (id) => {
    try {
      const { data } = await api.get(`/inscricoes/${id}/checklist`);
      const pessoas = Array.isArray(data)
        ? [{ pessoaChave: "candidato", nomeCompleto: usuario?.nome_completo || "Candidato", membroId: null, checklist: data }]
        : [
            { pessoaChave: "candidato", nomeCompleto: data.candidato?.nome_completo || usuario?.nome_completo || "Candidato", membroId: null, checklist: data.candidato?.checklist || [] },
            ...(data.membros || []).map((m) => ({ pessoaChave: `membro-${m.membro_id}`, nomeCompleto: m.nome_completo, membroId: m.membro_id, checklist: m.checklist || [] })),
          ];

      const flat = pessoas.flatMap((p) =>
        p.checklist.map((g) => ({ ...g, pessoaChave: p.pessoaChave, nomePessoa: p.nomeCompleto, membroId: p.membroId }))
      );
      setChecklist(flat);

      // Identifica se ainda há algum item em processamento pela IA
      const emProcessamento = {};
      let aindaTemProcessando = false;

      flat.forEach((grupo) => {
        if (grupo.status === "PROCESSANDO") {
          emProcessamento[grupo.chave] = true;
          aindaTemProcessando = true;
        }
        grupo.itens.forEach((item) => {
          if (item.status === "PROCESSANDO") {
            emProcessamento[item.documento_id || `${grupo.chave}-${item.solicitado_id}`] = true;
            aindaTemProcessando = true;
          }
        });
      });

      setProcessando(emProcessamento);
      return aindaTemProcessando;
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível carregar os documentos.");
      return false;
    } finally {
      setCarregando(false);
    }
  }, [usuario]);

  // ── agendamento de polling seguro (sem loop de re-render) ──
  const agendarPoll = useCallback((id) => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);

    pollTimerRef.current = setTimeout(async () => {
      const aindaProcessando = await carregarChecklist(id);
      if (aindaProcessando) {
        agendarPoll(id);
      }
    }, POLL_INTERVAL_MS);
  }, [carregarChecklist]);

  useEffect(() => {
    let ativo = true;

    async function iniciar() {
      try {
        const { data } = await api.get("/inscricoes/minha");
        if (!ativo) return;
        setInscricaoId(data.id);
        const aindaProcessando = await carregarChecklist(data.id);
        if (aindaProcessando && ativo) {
          agendarPoll(data.id);
        }
      } catch (err) {
        if (ativo) {
          setErro(err.response?.data?.detail || "Não foi possível carregar sua inscrição.");
          setCarregando(false);
        }
      }
    }

    iniciar();

    return () => {
      ativo = false;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [carregarChecklist, agendarPoll]);

  // ── seleção de arquivo ──────────────────────
  function abrirSeletor(key) { inputRefs.current[key]?.click(); }

  function lidarComSelecaoArquivo(solicitadoId, chaveItem, file, membroId = null) {
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setArquivosSelecionados((prev) => ({ ...prev, [chaveItem]: { file, previewUrl, solicitadoId, membroId } }));
  }

  function descartarArquivo(chaveItem) {
    setArquivosSelecionados((prev) => {
      const novo = { ...prev };
      if (novo[chaveItem]?.previewUrl) URL.revokeObjectURL(novo[chaveItem].previewUrl);
      delete novo[chaveItem];
      return novo;
    });
  }

  // ── envio em lote (retorna 202 rapidamente) ─
  async function enviarTudo() {
    setErro("");
    setEnviando(true);

    const chavesParaEnviar = Object.keys(arquivosSelecionados);
    const novosProcessando = { ...processando };

    for (const chave of chavesParaEnviar) {
      const item = arquivosSelecionados[chave];
      try {
        const formData = new FormData();
        formData.append("inscricao_id", inscricaoId);
        formData.append("solicitado_id", item.solicitadoId);
        if (item.membroId != null) formData.append("membro_id", item.membroId);
        formData.append("file", item.file);

        const { data } = await api.post("/documentos/upload", formData);
        if (data?.documento_id) {
          novosProcessando[data.documento_id] = true;
        }
      } catch (err) {
        setErro(err.response?.data?.detail || "Falha ao enviar um ou mais documentos.");
        setEnviando(false);
        await carregarChecklist(inscricaoId);
        return;
      }
    }

    setProcessando(novosProcessando);
    setArquivosSelecionados({});
    setEnviando(false);
    
    // Atualiza imediatamente e agenda o polling suave a cada 3s
    await carregarChecklist(inscricaoId);
    agendarPoll(inscricaoId);
  }

  const tudoAtendido =
    checklist.length > 0 &&
    checklist.every(
      (g) => !g.obrigatorio || g.status === "ENVIADO" || g.status === "ATENCAO"
    );
  const temPendentes = Object.keys(arquivosSelecionados).length > 0;
  const temProcessando = Object.keys(processando).length > 0;

  // ── render ──────────────────────────────────
  return (
    <main style={{ padding: "24px 16px", maxWidth: 680, margin: "0 auto", fontFamily: "Inter, system-ui, sans-serif", color: "#1f2937" }}>
      <div style={{ background: "#fff", padding: 28, borderRadius: 16, boxShadow: "0 4px 20px rgba(0,0,0,.05)", border: "1px solid #e5e7eb" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 20 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: "#e0e7ff", display: "flex", alignItems: "center", justifyContent: "center", color: "#4f46e5" }}>
                <FileUp size={18} />
              </div>
              <h1 style={{ fontSize: 22, margin: 0, fontWeight: 700, color: "#111827" }}>Envio de Documentos</h1>
            </div>
            <p style={{ color: "#6b7280", margin: 0, fontSize: 14 }}>
              Candidato: <strong>{usuario?.nome_completo || "—"}</strong>
            </p>
          </div>
          <button onClick={() => navigate("/dashboard")} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "transparent", border: "1px solid #e5e7eb", color: "#4b5563", padding: "7px 14px", borderRadius: 99, fontSize: 13, fontWeight: 500, cursor: "pointer" }}>
            <ArrowLeft size={14} /> Voltar
          </button>
        </div>

        {/* Banner de processamento global */}
        {temProcessando && (
          <div style={{ background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: 10, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "#3730a3" }}>
            <Loader2 size={18} style={{ animation: "spin 1s linear infinite", flexShrink: 0 }} />
            <div>
              <strong>Validação em andamento</strong> — A IA está analisando {Object.keys(processando).length} documento(s) em segundo plano. A página é atualizada automaticamente a cada {POLL_INTERVAL_MS / 1000} segundos.
            </div>
          </div>
        )}

        {/* Banner de dica */}
        <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "12px 14px", borderRadius: 10, fontSize: 13, color: "#166534", marginBottom: 20, lineHeight: 1.4 }}>
          💡 <strong>Dica:</strong> Tire fotos nítidas com boa iluminação. Nosso sistema analisa a legibilidade e autenticidade de cada documento em tempo real.
        </div>

        {erro && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#dc2626", padding: "12px 14px", borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
            <strong>Atenção:</strong> {erro}
          </div>
        )}

        {/* Lista de documentos */}
        {carregando ? (
          <div style={{ textAlign: "center", padding: "48px 0", color: "#6b7280" }}>
            <Loader2 size={28} style={{ animation: "spin 1s linear infinite", margin: "0 auto 12px", display: "block" }} />
            Carregando documentos…
          </div>
        ) : (
          <div style={{ marginTop: 16 }}>
            {checklist.map((grupo, index) => {
              const chaveGrupo = `${grupo.pessoaChave}-${grupo.chave}`;
              const primeiraPessoa = index === 0 || checklist[index - 1].pessoaChave !== grupo.pessoaChave;
              const grupoEmProcessamento =
                grupo.status === "PROCESSANDO" ||
                grupo.itens.some(
                  (it) => it.status === "PROCESSANDO" || (it.documento_id && processando[it.documento_id])
                );

              return (
                <div key={chaveGrupo} style={{ borderBottom: "1px solid #e5e7eb", paddingBottom: 24, marginBottom: 24 }}>
                  {primeiraPessoa && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "12px 0 16px", paddingBottom: 8, borderBottom: "2px solid #6366f1" }}>
                      <FileText size={18} style={{ color: "#6366f1" }} />
                      <h2 style={{ fontSize: 18, margin: 0, fontWeight: 700, color: "#111827" }}>
                        {grupo.pessoaChave === "candidato" ? "Meus Documentos (Titular)" : `Documentos de ${grupo.nomePessoa}`}
                      </h2>
                    </div>
                  )}

                  {/* Título do grupo */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
                    <div>
                      <h3 style={{ fontSize: 16, margin: "0 0 3px", fontWeight: 600, color: "#111827" }}>
                        {grupo.titulo}
                        {grupo.obrigatorio && <span style={{ color: "#dc2626", marginLeft: 4 }}>*</span>}
                      </h3>
                      {grupo.descricao && <p style={{ fontSize: 13, color: "#6b7280", margin: 0 }}>{grupo.descricao}</p>}
                    </div>
                    {grupo.itens.length === 1 && !grupoEmProcessamento && <StatusBadge status={grupo.status} />}
                    {grupoEmProcessamento && <StatusBadge status="PROCESSANDO" />}
                  </div>

                  {/* Feedback do grupo */}
                  {grupo.mensagem_feedback && !grupoEmProcessamento && (
                    <FeedbackBox nivel={grupo.nivel_alerta} mensagem={grupo.mensagem_feedback} />
                  )}

                  {/* Overlay de processamento */}
                  {grupoEmProcessamento && <ProcessingOverlay />}

                  {/* Cards de upload (ocultos enquanto processa) */}
                  {!grupoEmProcessamento && (
                    grupo.itens.length === 1 ? (
                      (() => {
                        const it = grupo.itens[0];
                        const inputKey = `${grupo.pessoaChave}-${it.solicitado_id}`;
                        const sel = arquivosSelecionados[chaveGrupo];
                        const isRejeitado = ["REJEITADO", "ERRO"].includes(grupo.status);
                        const isAtencao = grupo.status === "ATENCAO";
                        const isEnviado = grupo.status === "ENVIADO";

                        return (
                          <div style={{ background: "#f9fafb", border: `1px solid ${isRejeitado ? "#fecaca" : isAtencao ? "#fde68a" : "#e5e7eb"}`, padding: 16, borderRadius: 12, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 12 }}>
                            <input type="file" accept="image/*, .pdf" style={{ display: "none" }} ref={(el) => (inputRefs.current[inputKey] = el)} onChange={(e) => lidarComSelecaoArquivo(it.solicitado_id, chaveGrupo, e.target.files?.[0], grupo.membroId)} />

                            <span style={{ fontSize: 13, color: "#6b7280" }}>
                              {sel ? `📎 ${sel.file.name}` : isEnviado ? "Arquivo salvo com sucesso" : isRejeitado ? "Arquivo rejeitado — envie um documento válido" : "Nenhum arquivo enviado ainda"}
                            </span>

                            {!sel ? (
                              <button onClick={() => abrirSeletor(inputKey)} style={{ background: isRejeitado ? "#dc2626" : isAtencao ? "#d97706" : isEnviado ? "#f3f4f6" : "#6366f1", color: isEnviado ? "#374151" : "#fff", border: isEnviado ? "1px solid #d1d5db" : "none", padding: "9px 16px", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6 }}>
                                {isEnviado || isAtencao ? <><RefreshCw size={14} /> Substituir</> : isRejeitado ? <><FileUp size={14} /> Reenviar</> : <><FileUp size={14} /> Adicionar</>}
                              </button>
                            ) : (
                              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                                <span style={{ fontSize: 12, color: "#10b981", fontWeight: 700 }}>✓ Pronto</span>
                                <button onClick={() => descartarArquivo(chaveGrupo)} style={{ background: "#fef2f2", color: "#ef4444", border: "1px solid #fecaca", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
                                  <Trash2 size={13} /> Remover
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })()
                    ) : (
                      /* Múltiplos subitens (RG Frente + Verso) */
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 14, marginTop: 12 }}>
                        {grupo.itens.map((item) => {
                          const chaveItem = `${chaveGrupo}-${item.solicitado_id}`;
                          const inputKey = `${grupo.pessoaChave}-${item.solicitado_id}`;
                          const sel = arquivosSelecionados[chaveItem];
                          const itemProcessando =
                            item.status === "PROCESSANDO" ||
                            (item.documento_id && processando[item.documento_id]);

                          return (
                            <div key={item.solicitado_id} style={{ background: "#f9fafb", border: `1px solid ${item.status === "REJEITADO" ? "#fecaca" : item.status === "ATENCAO" ? "#fde68a" : "#e5e7eb"}`, padding: 16, borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", marginBottom: 10 }}>
                                <strong style={{ fontSize: 14, color: "#111827" }}>{item.rotulo || item.nome_documento}</strong>
                                <StatusBadge status={itemProcessando ? "PROCESSANDO" : item.status} />
                              </div>

                              {itemProcessando ? (
                                <ProcessingOverlay />
                              ) : (
                                <>
                                  <input type="file" accept="image/*" capture="environment" style={{ display: "none" }} ref={(el) => (inputRefs.current[inputKey] = el)} onChange={(e) => lidarComSelecaoArquivo(item.solicitado_id, chaveItem, e.target.files?.[0], grupo.membroId)} />

                                  {sel ? (
                                    <div style={{ width: "100%" }}>
                                      <img src={sel.previewUrl} alt="Preview" style={{ width: "100%", height: 100, objectFit: "cover", borderRadius: 8, marginBottom: 8, border: "2px solid #10b981" }} />
                                      <button onClick={() => descartarArquivo(chaveItem)} style={{ background: "#fef2f2", color: "#ef4444", border: "1px solid #fecaca", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 12, width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
                                        <Trash2 size={13} /> Descartar
                                      </button>
                                    </div>
                                  ) : (
                                    <button onClick={() => abrirSeletor(inputKey)} style={{ background: item.status === "ENVIADO" ? "#f3f4f6" : item.status === "REJEITADO" ? "#fef2f2" : "#e0e7ff", color: item.status === "ENVIADO" ? "#374151" : item.status === "REJEITADO" ? "#dc2626" : "#4338ca", border: item.status === "ENVIADO" ? "1px solid #d1d5db" : item.status === "REJEITADO" ? "1px solid #fca5a5" : "none", padding: "14px", borderRadius: 8, cursor: "pointer", width: "100%", fontWeight: 600, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                                      {item.status === "ENVIADO" ? <><RefreshCw size={14} /> Substituir foto</> : item.status === "REJEITADO" ? <><Camera size={14} /> Tirar nova foto</> : <><Camera size={14} /> Tirar foto / Galeria</>}
                                    </button>
                                  )}

                                  {/* Feedback individual do subitem */}
                                  {item.mensagem_feedback && (
                                    <FeedbackBox nivel={item.nivel_alerta} mensagem={item.mensagem_feedback} />
                                  )}
                                </>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Ações globais */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 24 }}>
          {temPendentes && (
            <button disabled={enviando} onClick={enviarTudo} style={{ background: enviando ? "#6ee7b7" : "#10b981", color: "#fff", border: "none", padding: 16, borderRadius: 12, fontWeight: 700, fontSize: 15, cursor: enviando ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              {enviando ? <><Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} /> Enviando para o servidor…</> : <><FileUp size={18} /> Salvar e Validar Fotos Selecionadas</>}
            </button>
          )}

          {temProcessando && !temPendentes && (
            <button disabled style={{ background: "#e0e7ff", color: "#4338ca", border: "none", padding: 16, borderRadius: 12, fontWeight: 700, fontSize: 15, cursor: "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} /> Aguardando validação da IA…
            </button>
          )}

          <button disabled={!tudoAtendido || temProcessando} onClick={() => navigate(`/auditoria/${inscricaoId}`)} style={{ background: tudoAtendido && !temProcessando ? "#4f46e5" : "#f3f4f6", color: tudoAtendido && !temProcessando ? "#fff" : "#9ca3af", border: "none", padding: 16, borderRadius: 12, fontWeight: 700, fontSize: 15, cursor: tudoAtendido && !temProcessando ? "pointer" : "not-allowed" }}>
            {temProcessando ? "Aguardando validações para prosseguir…" : tudoAtendido ? "Ir para Auditoria Final →" : "Envie todos os documentos obrigatórios para prosseguir"}
          </button>
        </div>

      </div>
    </main>
  );
}
