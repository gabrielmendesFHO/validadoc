import { Eye, EyeOff, Loader2, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState("");
  const [entrando, setEntrando] = useState(false);
  const navigate = useNavigate();
  async function handleSubmit(event) {
    event.preventDefault();
    if (entrando) return;
    setErro("");
    setEntrando(true);
    try {
      const body = new URLSearchParams({ username: email, password: senha });
      const { data } = await api.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        timeout: 90_000,
      });
      localStorage.setItem("access_token", data.access_token); localStorage.setItem("usuario", JSON.stringify(data.usuario)); onLogin(data.usuario);
      navigate(data.usuario?.perfil === "CANDIDATO" ? "/acompanhamento" : "/dashboard");
    } catch (err) {
      if (["ECONNABORTED", "ETIMEDOUT"].includes(err.code)) {
        setErro("O servidor demorou para responder. Aguarde alguns instantes e tente entrar novamente.");
      } else if (err.code === "ERR_NETWORK") {
        setErro("Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.");
      } else {
        setErro(err.response?.data?.detail || "Não foi possível fazer login.");
      }
    } finally {
      setEntrando(false);
    }
  }
  return <main className="login-page"><section className="login-brand-panel"><div className="login-logo"><ShieldCheck size={30} /> ValidaDoc</div><div className="login-brand-copy"><span>Segurança e transparência</span><h1>Documentos validados. Bolsas que chegam a quem precisa.</h1><p>Uma jornada simples, segura e acompanhada em cada etapa.</p></div><div className="login-art" aria-hidden="true"><LockKeyhole size={104} /></div></section><section className="login-form-panel"><form className="login-form" onSubmit={handleSubmit} aria-busy={entrando}><p className="login-kicker">Bem-vindo de volta</p><h2>Acesse sua conta</h2><p className="muted">Entre para acompanhar sua inscrição.</p><label>E-mail ou CPF<span className="field-with-icon"><Mail size={18}/><input name="username" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@instituicao.edu.br" required /></span></label><label>Senha<span className="field-with-icon"><LockKeyhole size={18}/><input name="password" autoComplete="current-password" type={mostrarSenha ? "text" : "password"} value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Sua senha" required /><button type="button" aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"} onClick={() => setMostrarSenha(!mostrarSenha)}>{mostrarSenha ? <EyeOff size={18}/> : <Eye size={18}/>}</button></span></label><a className="forgot-link" href="#recuperar">Esqueci minha senha</a>{erro && <div className="alert error-alert" role="alert">{erro}</div>}<button className="brand-button wide-button" type="submit" disabled={entrando}>{entrando && <Loader2 className="spin" size={17} aria-hidden="true"/>}{entrando ? "Entrando…" : "Entrar"}</button>{entrando && <p className="login-progress muted" role="status">Aguardando confirmação do acesso. O primeiro acesso pode levar alguns instantes.</p>}</form><footer>Instituição de Ensino · ValidaDoc © 2025</footer></section></main>;
}
