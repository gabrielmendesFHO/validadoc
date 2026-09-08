import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function UploadDocumento({ usuario }) {
  const navigate = useNavigate();
  const [inscricaoId, setInscricaoId] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  
  // Novos estados para previzualizacao e uploads
  const [arquivosSelecionados, setArquivosSelecionados] = useState({});
  const [enviando, setEnviando] = useState(false);
  const inputRefs = useRef({});

  async function carregarChecklist(id) {
    try {
      const { data } = await api.get(`/inscricoes/${id}/checklist`);
      setChecklist(data);
    } catch (err) {
      setErro(err.response?.data?.detail || "Nao foi possivel carregar os documentos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    async function iniciar() {
      try {
        const { data } = await api.get("/inscricoes/minha");
        setInscricaoId(data.id);
        await carregarChecklist(data.id);
      } catch (err) {
        setErro(err.response?.data?.detail || "Nao foi possivel carregar sua inscricao.");
        setCarregando(false);
      }
    }
    iniciar();
  }, []);

  function abrirSeletor(solicitadoId) {
    inputRefs.current[solicitadoId]?.click();
  }

  // Apenas retem no state antes de subir
  function lidarComSelecaoArquivo(solicitadoId, chaveItem, file) {
    if (!file) return;
    
    // Criar um preview URL para mostrar na tela
    const previewUrl = URL.createObjectURL(file);
    
    setArquivosSelecionados(prev => ({
      ...prev,
      [chaveItem]: { file, previewUrl, solicitadoId }
    }));
  }

  // Remove selecao
  function descartarArquivo(chaveItem) {
    setArquivosSelecionados(prev => {
      const novo = { ...prev };
      if(novo[chaveItem]?.previewUrl) URL.revokeObjectURL(novo[chaveItem].previewUrl);
      delete novo[chaveItem];
      return novo;
    });
  }

  // Funcao para salvar tudo de uma vez
  async function enviarTudo() {
    setErro("");
    setEnviando(true);
    
    const chavesParaEnviar = Object.keys(arquivosSelecionados);
    
    for (const chave of chavesParaEnviar) {
      const item = arquivosSelecionados[chave];
      try {
        const formData = new FormData();
        formData.append("inscricao_id", inscricaoId);
        formData.append("solicitado_id", item.solicitadoId);
        formData.append("file", item.file);
        
        await api.post("/documentos/upload", formData);
      } catch (err) {
        setErro(err.response?.data?.detail || "Erro ao enviar um ou mais documentos.");
        setEnviando(false);
        return; // interromper
      }
    }
    
    // Sucesso generalizado! Limpa uploads e atualiza a view
    setArquivosSelecionados({});
    await carregarChecklist(inscricaoId);
    setEnviando(false);
  }

  const tudoEnviadoNoBack =
    checklist.length > 0 &&
    checklist.every((grupo) => !grupo.obrigatorio || grupo.status === "ENVIADO");

  const temArquivosPendentes = Object.keys(arquivosSelecionados).length > 0;

  return (
    <main style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      <section>
        <div style={{ background: '#fff', padding: '24px', borderRadius: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div>
              <h1 style={{ fontSize: '24px', margin: '0 0 4px' }}>Envio de Documentos</h1>
              <p style={{ color: '#6b7280', margin: 0, fontSize: '14px' }}>Candidato: {usuario?.nome_completo || "—"}</p>
            </div>
            <button 
              onClick={() => navigate("/dashboard")}
              style={{
                background: 'transparent', border: '1px solid #e5e7eb', color: '#4b5563', 
                padding: '8px 16px', borderRadius: '99px', cursor: 'pointer'
              }}
            >
              Voltar
            </button>
          </div>

          <p style={{background: '#f8fafc', padding: '12px', borderRadius: '8px', fontSize: '14px', borderLeft: '4px solid #10b981', color: '#334155'}}>
            Tire foto da parte da frente e depois do verso. Revise e clique em 'Salvar Fotos'.
          </p>

          {erro && <div style={{ background: '#fef2f2', color: '#ef4444', padding: '12px', borderRadius: '8px', marginBottom: '20px' }}>{erro}</div>}

          {carregando ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>Carregando documentos...</div>
          ) : (
            <div style={{ marginTop: '24px' }}>
              {checklist.map((grupo) => (
                <div key={grupo.chave} style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '24px', marginBottom: '24px' }}>
                  <div style={{ marginBottom: '16px' }}>
                    <h2 style={{ fontSize: '18px', margin: '0 0 4px' }}>{grupo.titulo}</h2>
                    {grupo.descricao && <p style={{ fontSize: '14px', color: '#6b7280', margin: 0 }}>{grupo.descricao}</p>}
                  </div>

                  {grupo.itens.length === 1 ? (
                    // Caso tenha apenas 1 item
                    <div style={{ background: '#f9fafb', padding: '16px', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '14px', fontWeight: '500', color: grupo.status === "ENVIADO" ? '#10b981' : '#f59e0b' }}>
                        {grupo.status === "ENVIADO" ? "✓ Enviado" : "Pendente"}
                      </span>
                      
                      <input
                        type="file"
                        accept="image/*, .pdf"
                        style={{ display: "none" }}
                        ref={(el) => (inputRefs.current[grupo.itens[0].solicitado_id] = el)}
                        onChange={(e) => lidarComSelecaoArquivo(grupo.itens[0].solicitado_id, grupo.chave, e.target.files?.[0])}
                      />

                      {!arquivosSelecionados[grupo.chave] ? (
                         <button
                           style={{ background: '#6366f1', color: '#fff', border: 'none', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer' }}
                           onClick={() => abrirSeletor(grupo.itens[0].solicitado_id)}
                         >
                           Adicionar
                         </button>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 'bold' }}>Arquivo pronto</span>
                          <button style={{ background: '#fef2f2', color: '#ef4444', border: 'none', borderRadius: '8px', padding: '6px 12px', cursor: 'pointer', fontSize: '13px' }} onClick={() => descartarArquivo(grupo.chave)}>Remover</button>
                        </div>
                      )}
                    </div>
                  ) : (
                    // Caso tenha Subitens (Ex: RGFrente e RGVerso)
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      {grupo.itens.map((item) => {
                        const chaveItem = grupo.chave + "-" + item.solicitado_id;
                        const selecionado = arquivosSelecionados[chaveItem];

                        return (
                          <div key={item.solicitado_id} style={{ background: '#f9fafb', padding: '16px', borderRadius: '12px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <span style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>{item.rotulo}</span>
                            
                            {item.status === "ENVIADO" && !selecionado ? (
                              <div style={{ color: '#10b981', fontWeight: 'bold', fontSize: '13px', margin: '16px 0' }}>✓ Recebido</div>
                            ) : (
                              <>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment" // prioriza câmera traseira no celular
                                  style={{ display: "none" }}
                                  ref={(el) => (inputRefs.current[item.solicitado_id] = el)}
                                  onChange={(e) => lidarComSelecaoArquivo(item.solicitado_id, chaveItem, e.target.files?.[0])}
                                />
                                
                                {selecionado ? (
                                  <div style={{ width: '100%' }}>
                                    <img src={selecionado.previewUrl} alt="Preview" style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: '8px', marginBottom: '12px', border: '2px solid #10b981' }} />
                                    <button style={{ background: '#fef2f2', color: '#ef4444', border: 'none', borderRadius: '8px', padding: '6px 12px', cursor: 'pointer', fontSize: '13px', width: '100%' }} onClick={() => descartarArquivo(chaveItem)}>
                                      Trocar Foto
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    style={{ background: '#e0e7ff', color: '#4f46e5', border: 'none', padding: '24px 16px', borderRadius: '8px', cursor: 'pointer', width: '100%', fontWeight: '600' }}
                                    onClick={() => abrirSeletor(item.solicitado_id)}
                                  >
                                    Câmera/Galeria
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '32px' }}>
            
            {/* Se houver arquivos na "memória" para enviar */}
            {temArquivosPendentes && (
              <button
                style={{ background: '#10b981', color: '#fff', border: 'none', padding: '16px', borderRadius: '12px', fontWeight: 'bold', cursor: enviando ? 'not-allowed' : 'pointer' }}
                disabled={enviando}
                onClick={enviarTudo}
              >
                {enviando ? "Salvando Documentos..." : "Salvar Fotos"}
              </button>
            )}

            {/* Apenas mostra Botão de Avançar se tudo já estiver salvo no backend */}
            <button
              style={{ background: tudoEnviadoNoBack ? '#4f46e5' : '#e5e7eb', color: tudoEnviadoNoBack ? '#fff' : '#9ca3af', border: 'none', padding: '16px', borderRadius: '12px', fontWeight: 'bold', cursor: tudoEnviadoNoBack ? 'pointer' : 'not-allowed' }}
              disabled={!tudoEnviadoNoBack}
              onClick={() => navigate(`/auditoria/${inscricaoId}`)}
            >
              Próximo Passo
            </button>
            
          </div>
        </div>
      </section>
    </main>
  );
}
