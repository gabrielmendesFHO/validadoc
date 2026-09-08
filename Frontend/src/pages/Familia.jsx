import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, FileUp, Pencil, Plus, Save, Trash2, Users, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

const FORMULARIO_VAZIO = {
  nome_completo: "",
  parentesco: "",
  renda_declarada: "",
};

export default function Familia() {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState(null);
  const [membros, setMembros] = useState([]);
  const [formulario, setFormulario] = useState(FORMULARIO_VAZIO);
  const [membroEditando, setMembroEditando] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  async function carregarFamilia() {
    try {
      const { data: inscricao } = await api.get("/inscricoes/minha");
      setInscricaoId(inscricao.id);
      const { data } = await api.get(`/inscricoes/${inscricao.id}/membros`);
      setMembros(data);
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível carregar os membros da família.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregarFamilia();
  }, []);

  function alterarCampo(event) {
    const { name, value } = event.target;
    setFormulario((atual) => ({ ...atual, [name]: value }));
  }

  function iniciarEdicao(membro) {
    setMembroEditando(membro.id);
    setFormulario({
      nome_completo: membro.nome_completo || "",
      parentesco: membro.parentesco || "",
      renda_declarada: membro.renda_declarada ?? "",
    });
    setErro("");
  }

  function cancelarEdicao() {
    setMembroEditando(null);
    setFormulario(FORMULARIO_VAZIO);
    setErro("");
  }

  async function salvarMembro(event) {
    event.preventDefault();
    if (!inscricaoId) return;

    setSalvando(true);
    setErro("");
    const payload = {
      nome_completo: formulario.nome_completo.trim(),
      parentesco: formulario.parentesco.trim() || null,
      renda_declarada:
        formulario.renda_declarada === "" || formulario.renda_declarada === null
          ? null
          : Number(formulario.renda_declarada),
    };

    try {
      if (membroEditando) {
        await api.put(`/inscricoes/${inscricaoId}/membros/${membroEditando}`, payload);
      } else {
        await api.post(`/inscricoes/${inscricaoId}/membros`, payload);
      }
      cancelarEdicao();
      await carregarFamilia();
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível salvar o membro.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluirMembro(membro) {
    if (!window.confirm(`Tem certeza que deseja remover "${membro.nome_completo}" da família?`)) {
      return;
    }

    setErro("");
    try {
      await api.delete(`/inscricoes/${inscricaoId}/membros/${membro.id}`);
      if (membroEditando === membro.id) cancelarEdicao();
      await carregarFamilia();
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível excluir o membro.");
    }
  }

  return (
    <main
      style={{
        padding: "32px 16px",
        maxWidth: "680px",
        margin: "0 auto",
        fontFamily: "Inter, system-ui, -apple-system, sans-serif",
        color: "#1f2937",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          padding: "28px",
          borderRadius: "16px",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
          border: "1px solid #e5e7eb",
        }}
      >
        {/* Topo / Cabeçalho */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  background: "#e0e7ff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#4f46e5",
                }}
              >
                <Users size={18} />
              </div>
              <h1 style={{ margin: 0, fontSize: "22px", fontWeight: "700", color: "#111827" }}>
                Membros da família
              </h1>
            </div>
            <p style={{ margin: 0, color: "#6b7280", fontSize: "14px" }}>
              Cadastre quem mora com você e participará da composição da renda familiar.
            </p>
          </div>

          <button
            onClick={() => navigate("/dashboard")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "transparent",
              border: "1px solid #e5e7eb",
              color: "#4b5563",
              padding: "7px 14px",
              borderRadius: "99px",
              fontSize: "13px",
              fontWeight: "500",
              cursor: "pointer",
            }}
          >
            <ArrowLeft size={14} /> Voltar
          </button>
        </div>

        {erro && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              color: "#dc2626",
              padding: "12px 14px",
              borderRadius: "8px",
              marginBottom: "20px",
              fontSize: "14px",
            }}
          >
            {erro}
          </div>
        )}

        {/* Formulário de Adicionar / Editar */}
        <form
          onSubmit={salvarMembro}
          style={{
            background: "#f9fafb",
            border: membroEditando ? "2px solid #6366f1" : "1px solid #e5e7eb",
            borderRadius: "12px",
            padding: "20px",
            marginBottom: "28px",
            boxSizing: "border-box",
            width: "100%",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
            }}
          >
            <h2 style={{ fontSize: "16px", fontWeight: "600", margin: 0, color: "#111827" }}>
              {membroEditando ? "✏️ Editar membro da família" : "➕ Adicionar membro"}
            </h2>
            {membroEditando && (
              <span
                style={{
                  fontSize: "12px",
                  background: "#e0e7ff",
                  color: "#4338ca",
                  padding: "3px 8px",
                  borderRadius: "99px",
                  fontWeight: "600",
                }}
              >
                Modo de edição
              </span>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Campo 1: Nome Completo */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "13px", fontWeight: "500", color: "#374151" }}>
                Nome completo *
              </label>
              <input
                type="text"
                name="nome_completo"
                value={formulario.nome_completo}
                onChange={alterarCampo}
                placeholder="Ex.: Jocelina da Silva"
                required
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #d1d5db",
                  fontSize: "14px",
                  outline: "none",
                  background: "#ffffff",
                }}
              />
            </div>

            {/* Linha com 2 colunas: Parentesco e Renda */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "12px",
                width: "100%",
                boxSizing: "border-box",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", minWidth: 0 }}>
                <label style={{ fontSize: "13px", fontWeight: "500", color: "#374151" }}>
                  Parentesco
                </label>
                <input
                  type="text"
                  name="parentesco"
                  value={formulario.parentesco}
                  onChange={alterarCampo}
                  placeholder="Ex.: Mãe, Pai, Irmão(a)"
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid #d1d5db",
                    fontSize: "14px",
                    outline: "none",
                    background: "#ffffff",
                  }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", minWidth: 0 }}>
                <label style={{ fontSize: "13px", fontWeight: "500", color: "#374151" }}>
                  Renda mensal estimada (R$)
                </label>
                <input
                  type="number"
                  name="renda_declarada"
                  value={formulario.renda_declarada}
                  onChange={alterarCampo}
                  placeholder="0.00"
                  min="0"
                  step="0.01"
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid #d1d5db",
                    fontSize: "14px",
                    outline: "none",
                    background: "#ffffff",
                  }}
                />
              </div>
            </div>
          </div>

          {/* Botões do Formulário */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "8px",
              marginTop: "18px",
              flexWrap: "wrap",
            }}
          >
            {membroEditando && (
              <button
                type="button"
                onClick={cancelarEdicao}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#f3f4f6",
                  color: "#4b5563",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  padding: "9px 16px",
                  fontSize: "14px",
                  fontWeight: "500",
                  cursor: "pointer",
                }}
              >
                <X size={15} /> Cancelar
              </button>
            )}

            <button
              type="submit"
              disabled={salvando}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: salvando ? "#a5b4fc" : "#6366f1",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "10px 20px",
                fontSize: "14px",
                fontWeight: "600",
                cursor: salvando ? "not-allowed" : "pointer",
                boxShadow: "0 1px 3px rgba(0, 0, 0, 0.1)",
              }}
            >
              {salvando ? (
                "Salvando..."
              ) : membroEditando ? (
                <>
                  <Save size={15} /> Salvar alterações
                </>
              ) : (
                <>
                  <Plus size={15} /> Adicionar membro
                </>
              )}
            </button>
          </div>
        </form>

        {/* Lista de Membros Cadastrados */}
        <div>
          <h2
            style={{
              fontSize: "16px",
              fontWeight: "600",
              margin: "0 0 12px",
              color: "#111827",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span>Membros cadastrados ({membros.length})</span>
          </h2>

          {carregando ? (
            <p style={{ color: "#6b7280", fontSize: "14px" }}>Carregando membros...</p>
          ) : membros.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "32px 16px",
                border: "1px dashed #d1d5db",
                borderRadius: "12px",
                color: "#6b7280",
                fontSize: "14px",
              }}
            >
              <Users size={32} style={{ margin: "0 auto 8px", opacity: 0.4 }} />
              <p style={{ margin: 0, fontWeight: "500" }}>Nenhum membro cadastrado ainda.</p>
              <p style={{ margin: "4px 0 0", fontSize: "13px" }}>
                Preencha o formulário acima para adicionar quem reside com você.
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {membros.map((membro) => {
                const rendaNum =
                  membro.renda_declarada != null ? Number(membro.renda_declarada) : null;
                const estaEditandoEste = membroEditando === membro.id;

                return (
                  <div
                    key={membro.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "12px",
                      border: estaEditandoEste ? "2px solid #6366f1" : "1px solid #e5e7eb",
                      borderRadius: "10px",
                      padding: "14px 16px",
                      background: estaEditandoEste ? "#f5f3ff" : "#ffffff",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <strong style={{ fontSize: "15px", color: "#111827" }}>
                          {membro.nome_completo}
                        </strong>
                        {membro.parentesco && (
                          <span
                            style={{
                              fontSize: "12px",
                              background: "#f3f4f6",
                              color: "#4b5563",
                              padding: "2px 8px",
                              borderRadius: "99px",
                              fontWeight: "500",
                            }}
                          >
                            {membro.parentesco}
                          </span>
                        )}
                      </div>

                      <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: "13px" }}>
                        Renda mensal:{" "}
                        {rendaNum != null && rendaNum > 0 ? (
                          <strong style={{ color: "#059669" }}>
                            R$ {rendaNum.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                          </strong>
                        ) : (
                          <span>Sem renda informada (R$ 0,00)</span>
                        )}
                      </p>
                    </div>

                    <div style={{ display: "flex", gap: "6px" }}>
                      <button
                        onClick={() => iniciarEdicao(membro)}
                        title="Editar"
                        style={{
                          background: "#f3f4f6",
                          border: "1px solid #e5e7eb",
                          color: "#374151",
                          padding: "6px 10px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "13px",
                        }}
                      >
                        <Pencil size={14} /> Editar
                      </button>

                      <button
                        onClick={() => excluirMembro(membro)}
                        title="Excluir"
                        style={{
                          background: "#fef2f2",
                          border: "1px solid #fecaca",
                          color: "#dc2626",
                          padding: "6px 10px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "13px",
                        }}
                      >
                        <Trash2 size={14} /> Excluir
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Banner de Próximo Passo para Envio de Documentos */}
        {membros.length > 0 && (
          <div
            style={{
              marginTop: "28px",
              padding: "16px",
              background: "#ecfdf5",
              border: "1px solid #a7f3d0",
              borderRadius: "12px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <strong style={{ color: "#065f46", fontSize: "14px", display: "block" }}>
                ✓ Membros cadastrados com sucesso!
              </strong>
              <p style={{ margin: "2px 0 0", color: "#047857", fontSize: "13px" }}>
                Agora você já pode enviar os documentos (RG, Comprovantes) de cada familiar.
              </p>
            </div>

            <button
              onClick={() => navigate("/upload")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#10b981",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "10px 18px",
                fontSize: "14px",
                fontWeight: "600",
                cursor: "pointer",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              }}
            >
              <FileUp size={16} /> Ir para Envio de Documentos <ArrowRight size={15} />
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
