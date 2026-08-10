import json
import os
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AnalisesOcr, DocumentosEnviados, DocumentosSolicitados
from ..services.gemini_service import (
    GeminiExtractionError,
    avaliar_possivel_divergencia,
    extrair_dados_documento,
    lado_documento_invalido,
)
from ..services.image_processing import preparar_para_ia_multimodal

class SolicitadoDocumentoEnum(str, Enum):
    CNH = "CNH"
    RESIDENCIA = "RESIDENCIA"
    HOLERITE = "HOLERITE"
    RG = "RG"
    RG_VERSO = "RG_VERSO"


SOLICITADO_ID_POR_TIPO = {
    SolicitadoDocumentoEnum.CNH: 1,
    SolicitadoDocumentoEnum.RESIDENCIA: 2,
    SolicitadoDocumentoEnum.HOLERITE: 3,
    SolicitadoDocumentoEnum.RG: 4,
    SolicitadoDocumentoEnum.RG_VERSO: 5,
}


router = APIRouter(prefix="/documentos", tags=["Documentos"])

UPLOAD_DIR = "uploads/documentos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSOES_PERMITIDAS = (".png", ".jpg", ".jpeg", ".pdf")


@router.post("/upload")
async def upload_documento(
    inscricao_id: int = Form(...),
    solicitado_id: SolicitadoDocumentoEnum = Form(...),
    membro_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    solicitado_id_numero = SOLICITADO_ID_POR_TIPO[solicitado_id]
    # 1. Validação de extensão
    if not file.filename.lower().endswith(EXTENSOES_PERMITIDAS):
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado.")

    # 2. Confere se o documento solicitado existe e recupera a categoria
    #    (ex.: "RG", "HOLERITE") que define qual prompt/schema o Gemini usa
    solicitado = db.get(DocumentosSolicitados, solicitado_id_numero)
    if solicitado is None:
        raise HTTPException(status_code=400, detail="solicitado_id não encontrado.")

    # 3. Salva o arquivo original no disco (nunca é sobrescrito depois)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{inscricao_id}_{solicitado_id_numero}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # 4. Para RG, valida o lado antes de criar qualquer registro no banco.
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

    # 5. Registra o documento no banco antes de chamar a IA, pra já existir
    #    um documento_id pra vincular a análise (e pra não perder o registro
    #    do upload caso a extração falhe)
    try:
        novo_documento = DocumentosEnviados(
            inscricao_id=inscricao_id,
            solicitado_id=solicitado_id_numero,
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

    # 6. Pré-processamento leve (deskew + contraste, mantendo cor) — não
    #    sobrescreve o arquivo original, gera uma cópia à parte
    if caminho_para_ia is None:
        caminho_para_ia = preparar_para_ia_multimodal(file_path)

    # 7. Extração via Gemini
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
            status_auditoria=status_auditoria,  # veredito final (APTO/NAO_APTO) é da Fase 2, a nível de inscrição
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
        "status": novo_documento.status_processamento,
        "analise_id": analise.id,
        "dados_extraidos": dados_extraidos,
    }
