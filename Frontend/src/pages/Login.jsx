import { Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState("");
  const navigate = useNavigate();
  async function handleSubmit(event) {
    event.preventDefault(); setErro("");
    try {
      const body = new URLSearchParams({ username: email, password: senha });
      const { data } = await api.post("/auth/login", body, { headers: { "Content-Type": "application/x-www-form-urlencoded" } });
      localStorage.setItem("access_token", data.access_token); localStorage.setItem("usuario", JSON.stringify(data.usuario)); onLogin(data.usuario);
      navigate(data.usuario?.perfil === "CANDIDATO" ? "/acompanhamento" : "/dashboard");
    } catch (err) { setErro(err.response?.data?.detail || "Não foi possível fazer login."); }
  }
  return <main className="login-page"><section className="login-brand-panel"><div className="login-logo"><ShieldCheck size={30} /> ValidaDoc</div><div className="login-brand-copy"><span>Segurança e transparência</span><h1>Documentos validados. Bolsas que chegam a quem precisa.</h1><p>Uma jornada simples, segura e acompanhada em cada etapa.</p></div><div className="login-art" aria-hidden="true"><LockKeyhole size={104} /></div></section><section className="login-form-panel"><form className="login-form" onSubmit={handleSubmit}><p className="login-kicker">Bem-vindo de volta</p><h2>Acesse sua conta</h2><p className="muted">Entre para acompanhar sua inscrição.</p><label>E-mail ou CPF<span className="field-with-icon"><Mail size={18}/><input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@instituicao.edu.br" required /></span></label><label>Senha<span className="field-with-icon"><LockKeyhole size={18}/><input type={mostrarSenha ? "text" : "password"} value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Sua senha" required /><button type="button" aria-label="Mostrar senha" onClick={() => setMostrarSenha(!mostrarSenha)}>{mostrarSenha ? <EyeOff size={18}/> : <Eye size={18}/>}</button></span></label><a className="forgot-link" href="#recuperar">Esqueci minha senha</a>{erro && <div className="alert error-alert">{erro}</div>}<button className="brand-button wide-button" type="submit">Entrar</button></form><footer>Instituição de Ensino · ValidaDoc © 2025</footer></section></main>;
}
