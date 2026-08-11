import { ArrowLeft, CheckCircle2, FileUp, LoaderCircle, LogOut, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

const TIPOS = [
  ["RG", "RG frente"],
  ["RG_VERSO", "RG verso"],
  ["RESIDENCIA", "Residência"],
  ["HOLERITE", "Holerite"],
  ["CNH", "CNH"],
];

export default function UploadDocumento({ usuario, onLogout }) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState("");
  const [tipo, setTipo] = useState("RG");
  const [arquivo, setArquivo] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(event) {
    event.preventDefault();
    if (!arquivo) return setErro("Selecione um arquivo antes de enviar.");
    setErro("");
    setResultado(null);
    setEnviando(true);
    try {
      const formData = new FormData();
      formData.append("inscricao_id", inscricaoId);
      formData.append("solicitado_id", tipo);
      formData.append("file", arquivo);
      const { data } = await api.post("/documentos/upload", formData);
      setResultado(data);
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível processar o documento.");
    } finally {
      setEnviando(false);
    }
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand-lockup"><div className="brand-mark"><ShieldCheck size={20} /></div><div><strong>ValidaDoc</strong><span>Envio seguro de documentos</span></div></div>
      <div className="topbar-user"><span>{usuario?.nome_completo}</span><button className="icon-button" onClick={onLogout} title="Sair"><LogOut size={17} /></button></div>
    </header>
    <section className="page-content narrow-content">
      <button className="back-button" onClick={() => navigate("/dashboard")}><ArrowLeft size={16} /> Dashboard</button>
      <div className="page-heading"><div><p className="eyebrow">Análise documental</p><h1>Enviar documento</h1><p className="muted">O arquivo será pré-processado e analisado pela inteligência documental.</p></div></div>
      <form className="panel upload-panel" onSubmit={enviar}>
        <div className="form-grid">
          <label>Inscrição<input value={inscricaoId} onChange={(event) => setInscricaoId(event.target.value)} placeholder="Número da inscrição" inputMode="numeric" required /></label>
          <label>Tipo de documento<select value={tipo} onChange={(event) => setTipo(event.target.value)}>{TIPOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        </div>
        <label className="dropzone"><FileUp size={28} /><strong>{arquivo ? arquivo.name : "Escolha o arquivo"}</strong><span>PDF, JPG, JPEG ou PNG</span><input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setArquivo(event.target.files?.[0] || null)} /></label>
        {erro && <div className="alert error-alert">{erro}</div>}
        {resultado && <div className="alert success-alert"><CheckCircle2 size={18} /><div><strong>{resultado.message}</strong><span>Status: {resultado.status} · análise #{resultado.analise_id}</span></div></div>}
        <button className="primary-button wide-button" disabled={enviando || !arquivo}>{enviando ? <><LoaderCircle className="spin" size={17} /> Processando...</> : <><FileUp size={17} /> Enviar para análise</>}</button>
      </form>
    </section>
  </main>;
}
