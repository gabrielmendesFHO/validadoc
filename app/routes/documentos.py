import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AnalisesOcr, DocumentosEnviados, DocumentosSolicitados
from ..services.gemini_service import GeminiExtractionError, extrair_dados_documento
from ..services.image_processing import preparar_para_ia_multimodal

router = APIRouter(prefix="/documentos", tags=["Documentos"])

UPLOAD_DIR = "uploads/documentos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSOES_PERMITIDAS = (".png", ".jpg", ".jpeg", ".pdf")


@router.post("/upload")
async def upload_documento(
    inscricao_id: int = Form(...),
    solicitado_id: int = Form(...),
    membro_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Validação de extensão
    if not file.filename.lower().endswith(EXTENSOES_PERMITIDAS):
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado.")

    # 2. Confere se o documento solicitado existe e recupera a categoria
    #    (ex.: "RG", "HOLERITE") que define qual prompt/schema o Gemini usa
    solicitado = db.get(DocumentosSolicitados, solicitado_id)
    if solicitado is None:
        raise HTTPException(status_code=400, detail="solicitado_id não encontrado.")

    # 3. Salva o arquivo original no disco (nunca é sobrescrito depois)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{inscricao_id}_{solicitado_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # 4. Registra o documento no banco antes de chamar a IA, pra já existir
    #    um documento_id pra vincular a análise (e pra não perder o registro
    #    do upload caso a extração falhe)
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
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail="Erro de integridade: verifique se inscricao_id, solicitado_id ou membro_id existem no banco.",
        )

    # 5. Pré-processamento leve (deskew + contraste, mantendo cor) — não
    #    sobrescreve o arquivo original, gera uma cópia à parte
    caminho_para_ia = preparar_para_ia_multimodal(file_path)

    # 6. Extração via Gemini
    dados_extraidos = None
    try:
        dados_extraidos = extrair_dados_documento(caminho_para_ia, solicitado.nome_documento)
        novo_documento.status_processamento = "CONCLUIDO"
        analise = AnalisesOcr(
            documento_id=novo_documento.id,
            dados_extraidos=json.dumps(dados_extraidos, ensure_ascii=False),
            taxa_confianca=(dados_extraidos.get("legibilidade") or 0) / 100,
            status_auditoria="EXTRAIDO",  # veredito final (APTO/NAO_APTO) é da Fase 2, a nível de inscrição
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
