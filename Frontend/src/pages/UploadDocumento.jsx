import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function UploadDocumento({ usuario }) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [enviandoChave, setEnviandoChave] = useState(null);
  const inputRefs = useRef({});

  async function carregarChecklist(id) {
    try {
      const { data } = await api.get(`/inscricoes/${id}/checklist`);
      setChecklist(data);
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível carregar os documentos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    async function iniciar() {
      try {
        const { data } = await api.get("/inscricoes/minha");
        setInscricaoId(data.id);
        await carregarChecklist(data.id);
      } catch (err) {
        setErro(err.response?.data?.detail || "Não foi possível carregar sua inscrição.");
        setCarregando(false);
      }
    }
    iniciar();
  }, []);

  function abrirSeletor(solicitadoId) {
    inputRefs.current[solicitadoId]?.click();
  }

  async function enviarArquivo(solicitadoId, chaveEnvio, file) {
    if (!file) return;
    setErro("");
    setEnviandoChave(chaveEnvio);
    try {
      const formData = new FormData();
      formData.append("inscricao_id", inscricaoId);
      formData.append("solicitado_id", solicitadoId);
      formData.append("file", file);
      await api.post("/documentos/upload", formData);
      await carregarChecklist(inscricaoId);
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível enviar o documento.");
    } finally {
      setEnviandoChave(null);
    }
  }

  const tudoEnviado =
    checklist.length > 0 &&
    checklist.every((grupo) => !grupo.obrigatorio || grupo.status === "ENVIADO");

  return (
    <main className="app-shell">
      <section className="page-content">
        <div className="checklist-card">
          <div className="checklist-header">
            <div>
              <h1>Envio de Documentos</h1>
              <p className="muted">Candidato: {usuario?.nome_completo || "—"}</p>
            </div>
            <button className="btn-outline-dark" onClick={() => navigate("/dashboard")}>
              Voltar
            </button>
          </div>

          {erro && <div className="alert error-alert">{erro}</div>}

          {carregando ? (
            <div className="loading-state">Carregando documentos...</div>
          ) : (
            <div className="checklist-frame">
              {checklist.map((grupo) => (
                <div className="checklist-row" key={grupo.chave}>
                  <div className="checklist-row-info">
                    <h2>{grupo.titulo}</h2>
                    {grupo.descricao && <p>{grupo.descricao}</p>}
                  </div>

                  {grupo.itens.length === 1 ? (
                    <div className="checklist-row-action">
                      <span className={`badge ${grupo.status === "ENVIADO" ? "badge-success" : "badge-pending"}`}>
                        {grupo.status === "ENVIADO" ? "Enviado" : "Pendente"}
                      </span>
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        style={{ display: "none" }}
                        ref={(el) => (inputRefs.current[grupo.itens[0].solicitado_id] = el)}
                        onChange={(e) =>
                          enviarArquivo(grupo.itens[0].solicitado_id, grupo.chave, e.target.files?.[0])
                        }
                      />
                      <button
                        className={grupo.status === "ENVIADO" ? "btn-outline-blue" : "btn-solid-blue"}
                        onClick={() => abrirSeletor(grupo.itens[0].solicitado_id)}
                        disabled={enviandoChave === grupo.chave}
                      >
                        {enviandoChave === grupo.chave
                          ? "Enviando..."
                          : grupo.status === "ENVIADO"
                          ? "Substituir"
                          : "Fazer Upload"}
                      </button>
                    </div>
                  ) : (
                    <div className="checklist-subitens">
                      {grupo.itens.map((item) => {
                        const chaveItem = `${grupo.chave}-${item.solicitado_id}`;
                        return (
                          <div className="checklist-subitem" key={item.solicitado_id}>
                            <span className="sub-rotulo">{item.rotulo}</span>
                            <span className={`badge ${item.status === "ENVIADO" ? "badge-success" : "badge-pending"}`}>
                              {item.status === "ENVIADO" ? "Enviado" : "Pendente"}
                            </span>
                            <input
                              type="file"
                              accept=".pdf,.jpg,.jpeg,.png"
                              style={{ display: "none" }}
                              ref={(el) => (inputRefs.current[item.solicitado_id] = el)}
                              onChange={(e) => enviarArquivo(item.solicitado_id, chaveItem, e.target.files?.[0])}
                            />
                            <button
                              className={item.status === "ENVIADO" ? "btn-outline-blue" : "btn-solid-blue"}
                              onClick={() => abrirSeletor(item.solicitado_id)}
                              disabled={enviandoChave === chaveItem}
                            >
                              {enviandoChave === chaveItem
                                ? "Enviando..."
                                : item.status === "ENVIADO"
                                ? "Substituir"
                                : "Fazer Upload"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="checklist-footer">
            <button
              className="btn-solid-blue"
              disabled={!tudoEnviado}
              onClick={() => navigate(`/auditoria/${inscricaoId}`)}
            >
              Próximo
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}