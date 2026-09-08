import json
import mimetypes
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Response
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import (
    AnalisesOcr,
    DocumentoBinario,
    DocumentosEnviados,
    DocumentosSolicitados,
    Inscricoes,
    Usuarios,
)
from ..services.crypto import criptografar, descriptografar
from ..services.gemini_service import (
    GeminiExtractionError,
    avaliar_possivel_divergencia,
    extrair_dados_documento,
    lado_documento_invalido,
)
from ..services.image_processing import preparar_para_ia_multimodal

router = APIRouter(prefix="/documentos", tags=["Documentos"])

EXTENSOES_PERMITIDAS = (".png", ".jpg", ".jpeg", ".pdf")
TAMANHO_MAXIMO_DOCUMENTO = 15 * 1024 * 1024

_MIME_POR_EXTENSAO = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}

def _detectar_mime(nome_arquivo: str) -> str:
    nome = nome_arquivo.lower()
    for ext, mime in _MIME_POR_EXTENSAO.items():
        if nome.endswith(ext):
            return mime
    tipo, _ = mimetypes.guess_type(nome_arquivo)
    return tipo or "application/octet-stream"


@router.post("/upload")
async def upload_documento(
    inscricao_id: int = Form(...),
    solicitado_id: int = Form(...),
    membro_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    if not file.filename.lower().endswith(EXTENSOES_PERMITIDAS):
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado.")

    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    if usuario.perfil == "CANDIDATO" and inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

    solicitado = db.get(DocumentosSolicitados, solicitado_id)
    if solicitado is None or solicitado.processo_id != inscricao.processo_id:
        raise HTTPException(status_code=400, detail="solicitado_id inválido para esta inscrição.")

    conteudo_original = await file.read()
    if not conteudo_original:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo_original) > TAMANHO_MAXIMO_DOCUMENTO:
        raise HTTPException(
            status_code=413,
            detail="Arquivo muito grande. O tamanho máximo permitido é 15 MB.",
        )

    mime_type = _detectar_mime(file.filename)
    conteudo_para_ia, mime_para_ia = preparar_para_ia_multimodal(conteudo_original, file.filename, mime_type)

    # 1. SALVAR NO BANCO PRIMEIRO (Isolando a transação para evitar o WinError 10054)
    try:
        novo_documento = DocumentosEnviados(
            inscricao_id=inscricao_id,
            solicitado_id=solicitado_id,
            membro_id=membro_id,
            status_processamento="PROCESSANDO_IA",
        )
        db.add(novo_documento)
        db.flush() 

        binario = DocumentoBinario(
            documento_id=novo_documento.id,
            conteudo_criptografado=criptografar(conteudo_original),
            nome_arquivo_original=file.filename,
            mime_type=mime_type,
            tamanho_bytes=len(conteudo_original),
        )
        db.add(binario)
        db.commit()  # Efetiva a gravação e libera a transação ociosa
        db.refresh(novo_documento)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Erro de integridade: verifique se inscricao_id, solicitado_id ou membro_id existem no banco.",
        )
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="O banco de dados encerrou a conexão ao salvar o arquivo. Tente novamente ou reduza o tamanho do documento.",
        ) from exc

    # 2. CHAMADA DA IA E AUDITORIA (Operação demorada)
    dados_extraidos = None
    try:
        dados_extraidos = extrair_dados_documento(conteudo_para_ia, mime_para_ia, solicitado.nome_documento)
        
        # Validação específica de lado do RG
        if solicitado.nome_documento in {"RG", "RG_VERSO"} and lado_documento_invalido(dados_extraidos, solicitado.nome_documento):
            lado_esperado = "frente" if solicitado.nome_documento == "RG" else "verso"
            
            # Atualiza o banco antes de abortar para manter rastreabilidade
            novo_documento.status_processamento = "REJEITADO"
            novo_documento.mensagem_erro = f"Lado inválido. Esperado: {lado_esperado}."
            analise = AnalisesOcr(
                documento_id=novo_documento.id,
                status_auditoria="REJEITADO",
                parecer=novo_documento.mensagem_erro
            )
            db.add(analise)
            db.commit()
            
            raise HTTPException(
                status_code=422,
                detail=f"Documento inválido: envie o lado {lado_esperado} do RG.",
            )

        # Caminho de Sucesso
        novo_documento.status_processamento = "CONCLUIDO"
        status_auditoria = "POSSIVEL_DIVERGENCIA" if avaliar_possivel_divergencia(dados_extraidos, solicitado.nome_documento) else "EXTRAIDO"

        # Autopreenchimento: se for RG/CNH do próprio candidato, atualizamos os dados ausentes
        if novo_documento.membro_id is None and solicitado.nome_documento in {"RG", "CNH"}:
            candidato = db.get(Usuarios, inscricao.candidato_id)
            if candidato:
                nome_extraido = dados_extraidos.get("nome")
                cpf_extraido = dados_extraidos.get("cpf")
                
                if nome_extraido and (not candidato.nome_completo or candidato.nome_completo.startswith("Candidato (")):
                    candidato.nome_completo = nome_extraido
                
                if cpf_extraido and not candidato.cpf:
                    candidato.cpf = cpf_extraido
                
                db.add(candidato)

        analise = AnalisesOcr(
            documento_id=novo_documento.id,
            dados_extraidos=json.dumps(dados_extraidos, ensure_ascii=False),
            taxa_confianca=(dados_extraidos.get("legibilidade") or 0) / 100,
            status_auditoria=status_auditoria,
        )
        
    except GeminiExtractionError as exc:
        # Caminho de Falha na IA
        novo_documento.status_processamento = "ERRO_EXTRACAO"
        novo_documento.mensagem_erro = str(exc)[:500]
        analise = AnalisesOcr(
            documento_id=novo_documento.id,
            status_auditoria="ERRO",
            parecer=str(exc)[:500],
        )

    # 3. COMMIT FINAL DO RESULTADO
    db.add(analise)
    db.commit()
    db.refresh(novo_documento)
    db.refresh(analise)

    return {
        "message": "Documento processado" if novo_documento.status_processamento == "CONCLUIDO" else "Falha na extração/validação",
        "documento_id": novo_documento.id,
        "solicitado_id": solicitado_id,
        "status": novo_documento.status_processamento,
        "analise_id": analise.id,
        "dados_extraidos": dados_extraidos,
    }


@router.get("/{documento_id}/arquivo")
def baixar_arquivo(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    documento = db.get(DocumentosEnviados, documento_id)
    if documento is None or documento.binario is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    if usuario.perfil == "CANDIDATO" and documento.inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a este documento.")

    conteudo = descriptografar(documento.binario.conteudo_criptografado)
    return Response(
        content=conteudo,
        media_type=documento.binario.mime_type,
        headers={"Content-Disposition": f'inline; filename="{documento.binario.nome_arquivo_original}"'},
    )