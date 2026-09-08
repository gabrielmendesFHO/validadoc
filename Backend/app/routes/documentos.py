import json
import mimetypes
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..dependencies import get_current_user
from ..models import (
    AnalisesOcr,
    DocumentoBinario,
    DocumentosEnviados,
    DocumentosSolicitados,
    Inscricoes,
    MembrosFamilia,
    Usuarios,
)
from ..services.crypto import criptografar, descriptografar
from ..services.gemini_service import (
    GeminiExtractionError,
    extrair_dados_documento,
)
from ..services.image_processing import preparar_para_ia_multimodal
from ..services.validacao_documental import validar_documento_no_upload

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


def _processar_ia_em_background(
    documento_id: int,
    conteudo_para_ia: bytes,
    mime_para_ia: str,
    nome_documento: str,
    inscricao_id: int,
    candidato_id: int,
    membro_id: Optional[int],
):
    """Executa a extração via Gemini e a validação documental de forma assíncrona.

    Abre uma sessão própria de banco para não conflitar com a sessão da requisição
    que já foi encerrada no momento em que a background task começa.
    """
    db = SessionLocal()
    try:
        documento = db.get(DocumentosEnviados, documento_id)
        if documento is None:
            return

        # Chamada à IA
        dados_extraidos = extrair_dados_documento(conteudo_para_ia, mime_para_ia, nome_documento)

        candidato = db.get(Usuarios, candidato_id)
        membro = db.get(MembrosFamilia, membro_id) if membro_id else None
        outros_membros = db.query(MembrosFamilia).filter_by(inscricao_id=inscricao_id).all()

        valido, motivo_rejeicao, nivel_alerta, mensagem_feedback = validar_documento_no_upload(
            categoria=nome_documento,
            dados_extraidos=dados_extraidos,
            candidato=candidato,
            membro=membro,
            outros_membros=outros_membros,
        )

        if not valido:
            documento.status_processamento = "REJEITADO"
            documento.mensagem_erro = motivo_rejeicao
            analise = AnalisesOcr(
                documento_id=documento_id,
                status_auditoria="REJEITADO",
                parecer=motivo_rejeicao,
                dados_extraidos=json.dumps(dados_extraidos, ensure_ascii=False),
            )
        else:
            documento.status_processamento = "CONCLUIDO"
            documento.mensagem_erro = mensagem_feedback if nivel_alerta == "aviso" else None
            status_auditoria = "POSSIVEL_DIVERGENCIA" if nivel_alerta == "aviso" else "EXTRAIDO"

            # Autopreenchimento de nome e CPF do candidato a partir do RG/CNH
            if membro_id is None and nome_documento in {"RG", "CNH"} and candidato:
                nome_extraido = dados_extraidos.get("nome")
                cpf_extraido = dados_extraidos.get("cpf")
                if nome_extraido and (
                    not candidato.nome_completo or candidato.nome_completo.startswith("Candidato (")
                ):
                    candidato.nome_completo = nome_extraido
                if cpf_extraido and not candidato.cpf:
                    candidato.cpf = cpf_extraido
                db.add(candidato)

            analise = AnalisesOcr(
                documento_id=documento_id,
                dados_extraidos=json.dumps(dados_extraidos, ensure_ascii=False),
                taxa_confianca=(dados_extraidos.get("legibilidade") or 0) / 100,
                status_auditoria=status_auditoria,
                parecer=mensagem_feedback,
            )

        db.add(documento)
        db.add(analise)
        db.commit()

    except GeminiExtractionError as exc:
        try:
            documento = db.get(DocumentosEnviados, documento_id)
            if documento:
                documento.status_processamento = "ERRO_EXTRACAO"
                documento.mensagem_erro = str(exc)[:500]
                analise = AnalisesOcr(
                    documento_id=documento_id,
                    status_auditoria="ERRO",
                    parecer=f"Não foi possível extrair os dados do documento. A IA retornou: {str(exc)[:300]}",
                )
                db.add(documento)
                db.add(analise)
                db.commit()
        except Exception:
            db.rollback()
    except Exception:
        db.rollback()
    finally:
        db.close()


@router.post("/upload", status_code=202)
async def upload_documento(
    background_tasks: BackgroundTasks,
    inscricao_id: int = Form(...),
    solicitado_id: int = Form(...),
    membro_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    """Salva o arquivo e retorna imediatamente. A IA processa em segundo plano."""
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

    # Anti-Fraude: bloquear arquivo byte-a-byte idêntico a outro já enviado nesta inscrição
    outros_binarios = (
        db.query(DocumentoBinario)
        .join(DocumentosEnviados)
        .filter(
            DocumentosEnviados.inscricao_id == inscricao_id,
            (DocumentosEnviados.solicitado_id != solicitado_id)
            | (DocumentosEnviados.membro_id != membro_id),
        )
        .all()
    )
    for outro in outros_binarios:
        if outro.tamanho_bytes == len(conteudo_original):
            try:
                if descriptografar(outro.conteudo_criptografado) == conteudo_original:
                    raise HTTPException(
                        status_code=422,
                        detail="Arquivo duplicado: este arquivo já foi enviado para outro documento desta inscrição.",
                    )
            except (ValueError, Exception):
                pass

    mime_type = _detectar_mime(file.filename)
    conteudo_para_ia, mime_para_ia = preparar_para_ia_multimodal(
        conteudo_original, file.filename, mime_type
    )

    # Salvar no banco com status PROCESSANDO_IA e retornar imediatamente
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
        db.commit()
        db.refresh(novo_documento)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Erro de integridade: verifique se inscricao_id, solicitado_id ou membro_id existem.",
        )
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="O banco encerrou a conexão ao salvar. Tente novamente ou reduza o tamanho do arquivo.",
        ) from exc

    # Agenda a IA para rodar em background (não bloqueia a resposta)
    background_tasks.add_task(
        _processar_ia_em_background,
        novo_documento.id,
        conteudo_para_ia,
        mime_para_ia,
        solicitado.nome_documento,
        inscricao_id,
        inscricao.candidato_id,
        membro_id,
    )

    return {
        "message": "Arquivo recebido. A validação está sendo processada em segundo plano.",
        "documento_id": novo_documento.id,
        "solicitado_id": solicitado_id,
        "membro_id": membro_id,
        "status": "PROCESSANDO_IA",
    }


@router.get("/{documento_id}/status")
def status_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    """Retorna o status atual de processamento de um documento (para polling do frontend)."""
    documento = db.get(DocumentosEnviados, documento_id)
    if documento is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    if usuario.perfil == "CANDIDATO" and documento.inscricao.candidato_id != usuario.id:
        raise HTTPException(status_code=403, detail="Sem acesso.")

    ultima_analise = (
        db.query(AnalisesOcr)
        .filter_by(documento_id=documento_id)
        .order_by(AnalisesOcr.criado_em.desc())
        .first()
    )

    nivel_alerta = None
    if documento.status_processamento == "CONCLUIDO":
        nivel_alerta = "aviso" if ultima_analise and ultima_analise.status_auditoria == "POSSIVEL_DIVERGENCIA" else "sucesso"
    elif documento.status_processamento in {"REJEITADO", "ERRO_EXTRACAO"}:
        nivel_alerta = "erro"

    return {
        "documento_id": documento_id,
        "status": documento.status_processamento,
        "nivel_alerta": nivel_alerta,
        "mensagem_feedback": (ultima_analise.parecer if ultima_analise else documento.mensagem_erro),
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