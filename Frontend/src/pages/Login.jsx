import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(null);
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setErro(null);

    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", senha);

      const { data } = await api.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("usuario", JSON.stringify(data.usuario));
      onLogin(data.usuario);
      navigate("/dashboard");
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível fazer login.");
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-card auth-card--split">
        <div className="auth-form-col">
                    <div className="auth-form-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
            <button
              onClick={() => navigate("/")}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px', 
                background: 'transparent', border: '1px solid #e5e7eb', 
                color: '#4b5563', padding: '6px 14px', borderRadius: '99px',
                fontSize: '14px', fontWeight: '500', cursor: 'pointer'
              }}
            >
              ← Voltar
            </button>
            <p className="auth-wordmark" style={{ margin: 0, fontWeight: 800, color: '#10b981' }}>VOCR'S</p>
          </div>
          <h1>Acesso ao sistema</h1>
          <p className="muted">Entre com suas credenciais para validar documentos.</p>

          <form onSubmit={handleSubmit}>
            <div className="auth-underline-field">
              <input
                type="email"
                placeholder="Digite seu e-mail"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="auth-underline-field">
              <input
                type="password"
                placeholder="Digite sua senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
            </div>

            <a className="auth-forgot" style={{ color: "#6366f1", textDecoration: "none", alignSelf: "flex-start", marginBottom: "20px" }} href="#esqueci-senha">
              Esqueci minha senha
            </a>

            {erro && <div className="alert error-alert">{erro}</div>}

            <button className="auth-submit" style={{ background: "#10b981", color: "#fff", border: "none", borderRadius: "12px", padding: "14px", fontWeight: "bold" }} type="submit">
              Entrar
            </button>
          </form>
        </div>

        <aside className="auth-info-col">
          <h2>Análise automatizada de documentos</h2>
          <p>
            Valide recibos de vencimento, comprovativos e documentos de
            identificação utilizando Visão Computacional e OCR. Reduza
            fraudes e acelere a concessão de bolsas com alta precisão.
          </p>
        </aside>
      </div>
    </main>
  );
}
