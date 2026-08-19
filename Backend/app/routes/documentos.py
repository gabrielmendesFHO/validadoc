import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import PROJECT_ROOT
from ..db import get_db
from ..dependencies import get_current_user
from ..models import AnalisesOcr, DocumentosEnviados, DocumentosSolicitados, Inscricoes, Usuarios
from ..services.gemini_service import (
    GeminiExtractionError,
    avaliar_possivel_divergencia,
    extrair_dados_documento,
    lado_documento_invalido,
)
from ..services.image_processing import preparar_para_ia_multimodal

router = APIRouter(prefix="/documentos", tags=["Documentos"])

UPLOAD_DIR = str(PROJECT_ROOT / "uploads" / "documentos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSOES_PERMITIDAS = (".png", ".jpg", ".jpeg", ".pdf")


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

    # solicitado_id precisa pertencer ao mesmo processo da inscrição — evita
    # que um id de outro processo seja usado por engano (ou de propósito).
    solicitado = db.get(DocumentosSolicitados, solicitado_id)
    if solicitado is None or solicitado.processo_id != inscricao.processo_id:
        raise HTTPException(status_code=400, detail="solicitado_id inválido para esta inscrição.")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{inscricao_id}_{solicitado_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    caminho_para_ia = None
    dados_pre_extraidos = None
    if solicitado.nome_documento in {"RG", "RG_VERSO"}:
        caminho_para_ia = preparar_para_ia_multimodal(file_path)
        try:
            dados_pre_extraidos = extrair_dados_documento(caminho_para_ia, solicitado.nome_documento)
        except GeminiExtractionError as exc:
            for caminho in {file_path, caminho_para_ia}:
                if caminho and os.path.exists(caminho):
                    os.remove(caminho)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if lado_documento_invalido(dados_pre_extraidos, solicitado.nome_documento):
            for caminho in {file_path, caminho_para_ia}:
                if caminho and os.path.exists(caminho):
                    os.remove(caminho)
            lado_esperado = "frente" if solicitado.nome_documento == "RG" else "verso"
            raise HTTPException(
                status_code=422,
                detail=f"Documento inválido: envie o lado {lado_esperado} do RG.",
            )

    try:
        novo_documento = DocumentosEnviados(
            inscricao_id=inscricao_id,
            solicitado_id=solicitado_id,
            membro_id=membro_id,
            caminho_arquivo=file_path,
            status_processamento="PROCESSANDO",
        )
        db.add(novo_documento)
        db.commit()
        db.refresh(novo_documento)
    except IntegrityError:
        db.rollback()
        for caminho in {file_path, caminho_para_ia}:
            if caminho and os.path.exists(caminho):
                os.remove(caminho)
        raise HTTPException(
            status_code=400,
            detail="Erro de integridade: verifique se inscricao_id, solicitado_id ou membro_id existem no banco.",
        )

    if caminho_para_ia is None:
        caminho_para_ia = preparar_para_ia_multimodal(file_path)

    dados_extraidos = dados_pre_extraidos
    try:
        if dados_extraidos is None:
            dados_extraidos = extrair_dados_documento(caminho_para_ia, solicitado.nome_documento)
        novo_documento.status_processamento = "CONCLUIDO"

        status_auditoria = "EXTRAIDO"
        if avaliar_possivel_divergencia(dados_extraidos, solicitado.nome_documento):
            status_auditoria = "POSSIVEL_DIVERGENCIA"

        analise = AnalisesOcr(
            documento_id=novo_documento.id,
            dados_extraidos=json.dumps(dados_extraidos, ensure_ascii=False),
            taxa_confianca=(dados_extraidos.get("legibilidade") or 0) / 100,
            status_auditoria=status_auditoria,
        )
    except GeminiExtractionError as exc:
        novo_documento.status_processamento = "ERRO_EXTRACAO"
        novo_documento.mensagem_erro = str(exc)[:500]
        analise = AnalisesOcr(
            documento_id=novo_documento.id,
            status_auditoria="ERRO",
            parecer=str(exc)[:500],
        )

    db.add(analise)
    db.commit()
    db.refresh(novo_documento)
    db.refresh(analise)

    return {
        "message": "Documento processado" if novo_documento.status_processamento == "CONCLUIDO" else "Falha na extração",
        "documento_id": novo_documento.id,
        "solicitado_id": solicitado_id,
        "status": novo_documento.status_processamento,
        "analise_id": analise.id,
        "dados_extraidos": dados_extraidos,
    }