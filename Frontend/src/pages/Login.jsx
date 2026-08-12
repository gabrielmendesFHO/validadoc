import { ShieldCheck } from "lucide-react";
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
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark">
            <ShieldCheck size={20} />
          </div>
          <strong>ValidaDoc</strong>
        </div>

        <h1>Acesso ao sistema</h1>
        <p className="muted">Entre com suas credenciais para validar documentos.</p>

        <form onSubmit={handleSubmit}>
          <label className="auth-field">
            E-mail
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="auth-field">
            Senha
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />
          </label>

          {erro && <div className="alert error-alert">{erro}</div>}

          <button className="primary-button wide-button" type="submit">
            Entrar
          </button>
        </form>
      </div>
    </main>
  );
}