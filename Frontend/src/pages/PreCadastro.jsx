import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus, ShieldCheck, ArrowLeft, Check } from "lucide-react";
import api from "../api/client";

export default function PreCadastro() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [nomeCompleto, setNomeCompleto] = useState("");
  const [cpf, setCpf] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setErro(null);
    setSucesso(null);
    setCarregando(true);

    try {
      const { data } = await api.post("/auth/registrar", {
        email,
        senha,
        nome_completo: nomeCompleto || undefined,
        cpf: cpf || undefined,
      });

      setSucesso(`Candidato "${data.nome_completo}" (${data.email}) cadastrado com sucesso!`);
      // Limpa o formulário para facilitar múltiplos cadastros seguidos
      setEmail("");
      setSenha("");
      setNomeCompleto("");
      setCpf("");
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível realizar o pré-cadastro.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-card auth-card--split">

        {/* Coluna do formulário */}
        <div className="auth-form-col">
          <div
            className="auth-form-header"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "28px",
            }}
          >
            <button
              onClick={() => navigate("/dashboard")}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                background: "transparent", border: "1px solid #e5e7eb",
                color: "#4b5563", padding: "6px 14px", borderRadius: "99px",
                fontSize: "14px", fontWeight: "500", cursor: "pointer",
              }}
            >
              <ArrowLeft size={14} /> Voltar
            </button>
            <p className="auth-wordmark" style={{ margin: 0, fontWeight: 800, color: "#10b981" }}>
              ValidaDoc
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <div
              style={{
                width: "36px", height: "36px", borderRadius: "10px",
                background: "#ecfdf5", display: "flex", alignItems: "center",
                justifyContent: "center", color: "#10b981", flexShrink: 0,
              }}
            >
              <UserPlus size={18} />
            </div>
            <h1 style={{ margin: 0, fontSize: "22px" }}>Pré-cadastro de candidato</h1>
          </div>
          <p className="muted" style={{ marginBottom: "24px" }}>
            Crie o acesso inicial. O candidato poderá atualizar seus dados ao enviar os documentos.
          </p>

          <form onSubmit={handleSubmit}>
            {/* E-mail — obrigatório */}
            <div className="auth-underline-field">
              <input
                type="email"
                placeholder="E-mail do candidato *"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {/* Senha inicial — obrigatório */}
            <div className="auth-underline-field">
              <input
                type="password"
                placeholder="Senha inicial *"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <p className="muted" style={{ fontSize: "12px", marginTop: "-8px", marginBottom: "16px" }}>
              Os campos abaixo são opcionais — serão preenchidos automaticamente quando o candidato enviar o RG/CNH.
            </p>

            {/* Nome — opcional */}
            <div className="auth-underline-field">
              <input
                type="text"
                placeholder="Nome completo (opcional)"
                value={nomeCompleto}
                onChange={(e) => setNomeCompleto(e.target.value)}
              />
            </div>

            {/* CPF — opcional */}
            <div className="auth-underline-field">
              <input
                type="text"
                placeholder="CPF (opcional)"
                value={cpf}
                onChange={(e) => setCpf(e.target.value)}
                maxLength={14}
              />
            </div>

            {erro && <div className="alert error-alert">{erro}</div>}

            {sucesso && (
              <div
                className="alert"
                style={{
                  background: "var(--success-bg)",
                  border: "1px solid var(--success-border)",
                  color: "var(--success)",
                  display: "flex", alignItems: "center", gap: "8px",
                  borderRadius: "8px", padding: "10px 14px", marginBottom: "16px",
                  fontSize: "14px",
                }}
              >
                <Check size={16} />
                {sucesso}
              </div>
            )}

            <button
              className="auth-submit"
              style={{
                background: carregando ? "#6ee7b7" : "#10b981",
                color: "#fff", border: "none", borderRadius: "12px",
                padding: "14px", fontWeight: "bold", cursor: carregando ? "not-allowed" : "pointer",
              }}
              type="submit"
              disabled={carregando}
            >
              {carregando ? "Cadastrando…" : "Cadastrar candidato"}
            </button>
          </form>
        </div>

        {/* Coluna informativa */}
        <aside className="auth-info-col">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <ShieldCheck size={22} style={{ color: "#10b981" }} />
            <h2 style={{ margin: 0 }}>Fluxo de pré-cadastro</h2>
          </div>
          <p style={{ marginBottom: "20px" }}>
            O admin cria o acesso com e-mail e senha. O sistema preenche os
            demais dados automaticamente à medida que o candidato envia seus documentos.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {[
              { n: "1", titulo: "Admin pré-cadastra", desc: "E-mail + senha inicial para o candidato acessar o portal." },
              { n: "2", titulo: "Candidato faz login", desc: "Acessa com as credenciais recebidas e vê o checklist de documentos." },
              { n: "3", titulo: "Envia o RG ou CNH", desc: "O sistema lê o documento e preenche nome e CPF automaticamente." },
              { n: "4", titulo: "Analista audita", desc: "Com todos os documentos enviados, o parecer final é gerado." },
            ].map(({ n, titulo, desc }) => (
              <div key={n} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <span
                  style={{
                    width: "24px", height: "24px", borderRadius: "50%",
                    background: "rgba(16,185,129,0.15)", color: "#10b981",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "12px", fontWeight: "700", flexShrink: 0, marginTop: "1px",
                  }}
                >
                  {n}
                </span>
                <div>
                  <strong style={{ fontSize: "14px" }}>{titulo}</strong>
                  <p className="muted" style={{ margin: 0, fontSize: "13px" }}>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </aside>

      </div>
    </main>
  );
}

