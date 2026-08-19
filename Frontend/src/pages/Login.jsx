import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

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
      <div className="auth-card auth-card--split">
        <div className="auth-form-col">
          <p className="auth-wordmark">VOCR'S</p>
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

            <a className="auth-forgot" href="#esqueci-senha">
              Esqueci minha senha
            </a>

            {erro && <div className="alert error-alert">{erro}</div>}

            <button className="auth-submit" type="submit">
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