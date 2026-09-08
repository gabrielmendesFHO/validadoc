import { useEffect, useState } from "react";
import { ArrowLeft, Pencil, Plus, Save, Trash2, X } from "lucide-react";
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
      renda_declarada: formulario.renda_declarada === "" ? null : Number(formulario.renda_declarada),
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
    if (!window.confirm(`Excluir ${membro.nome_completo} da família?`)) return;

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
    <main className="auth-shell">
      <div className="auth-card" style={{ width: "min(100%, 760px)", padding: "32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", marginBottom: "28px" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "26px" }}>Membros da família</h1>
            <p className="muted" style={{ marginTop: "6px" }}>Cadastre quem participará da composição da renda familiar.</p>
          </div>
          <button className="icon-button" onClick={() => navigate("/dashboard")} title="Voltar">
            <ArrowLeft size={17} />
          </button>
        </div>

        {erro && <div className="alert error-alert" style={{ marginBottom: "18px" }}>{erro}</div>}

        <form onSubmit={salvarMembro} style={{ border: "1px solid #e5e7eb", borderRadius: "12px", padding: "18px", marginBottom: "28px" }}>
          <h2 style={{ fontSize: "17px", margin: "0 0 16px" }}>
            {membroEditando ? "Editar membro" : "Adicionar membro"}
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "12px" }}>
            <input name="nome_completo" value={formulario.nome_completo} onChange={alterarCampo} placeholder="Nome completo" required />
            <input name="parentesco" value={formulario.parentesco} onChange={alterarCampo} placeholder="Parentesco" />
            <input name="renda_declarada" value={formulario.renda_declarada} onChange={alterarCampo} placeholder="Renda mensal" type="number" min="0" step="0.01" />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
            {membroEditando && (
              <button type="button" className="secondary-button" onClick={cancelarEdicao}>
                <X size={15} /> Cancelar
              </button>
            )}
            <button type="submit" className="primary-button" disabled={salvando}>
              {membroEditando ? <Save size={15} /> : <Plus size={15} />}
              {salvando ? "Salvando..." : membroEditando ? "Salvar alterações" : "Adicionar membro"}
            </button>
          </div>
        </form>

        {carregando ? (
          <p className="muted">Carregando membros...</p>
        ) : membros.length === 0 ? (
          <p className="muted" style={{ textAlign: "center", padding: "24px 0" }}>Nenhum membro cadastrado.</p>
        ) : (
          <div style={{ display: "grid", gap: "10px" }}>
            {membros.map((membro) => (
              <div key={membro.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "14px 16px" }}>
                <div>
                  <strong>{membro.nome_completo}</strong>
                  <p className="muted" style={{ marginTop: "4px", fontSize: "13px" }}>
                    {membro.parentesco || "Parentesco não informado"} {membro.renda_declarada != null ? `· R$ ${Number(membro.renda_declarada).toFixed(2).replace(".", ",")}` : ""}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button className="icon-button" onClick={() => iniciarEdicao(membro)} title="Editar">
                    <Pencil size={15} />
                  </button>
                  <button className="icon-button" onClick={() => excluirMembro(membro)} title="Excluir" style={{ color: "#dc2626" }}>
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
