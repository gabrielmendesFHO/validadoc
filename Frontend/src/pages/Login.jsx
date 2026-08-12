import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import "./Login.css";

export default function Login() {
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
      navigate("/dashboard");
    } catch (err) {
      setErro(err.response?.data?.detail || "Não foi possível fazer login.");
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        {/* Left column: form */}
        <div className="auth-form-panel">
          <div className="auth-brand">VOCR'S</div>

          <h1>Acesso ao sistema</h1>
          <p className="muted">
            Entre com suas credenciais para validar documentos.
          </p>

          <form onSubmit={handleSubmit}>
            <input
              className="auth-input"
              type="email"
              placeholder="Digite seu e-mail"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              className="auth-input"
              type="password"
              placeholder="Digite sua senha"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />

            <button
              type="button"
              className="forgot-password-link"
              onClick={() => navigate("/esqueci-senha")}
            >
              Esqueci minha senha
            </button>

            {erro && <div className="alert error-alert">{erro}</div>}

            <button className="primary-button" type="submit">
              Entrar
            </button>
          </form>
        </div>

        {/* Right column: info panel */}
        <aside className="auth-info-panel">
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