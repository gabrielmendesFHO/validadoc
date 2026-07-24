import os
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime

# Importe seus modelos e sessão do db.py e models.py
from app.db import get_db
from app.models import DocumentosEnviados
from ..services.image_processing import processar_imagem_para_ocr

router = APIRouter(prefix="/documentos", tags=["Documentos"])

UPLOAD_DIR = "uploads/documentos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_documento(
    inscricao_id: int = Form(...),
    solicitado_id: int = Form(...),
    membro_id: int = Form(None), # Opcional
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validação simples de extensão
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado.")

    # 2. Gerar nome de arquivo único
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{inscricao_id}_{solicitado_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # 3. Salvar o arquivo no disco
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # 4. (Opcional - Espaço para o Pré-processamento com OpenCV)
    # Aqui vai entrar a sua lógica de binarização e alinhamento antes do OCR
    # ex: processar_imagem(file_path)
    processamento_ok = processar_imagem_para_ocr(file_path)

    # Define um status baseado no sucesso do pré-processamento
    status_atual = "PROCESSAMENTO_OK" if processamento_ok else "ERRO_PROCESSAMENTO"

    # 5. Salvar o registro no Banco de Dados
    try:
        novo_documento = DocumentosEnviados(
            inscricao_id=inscricao_id,
            solicitado_id=solicitado_id,
            membro_id=membro_id,
            caminho_arquivo=file_path,
            status_processamento=status_atual
        )
        
        db.add(novo_documento)
        db.commit()
        db.refresh(novo_documento)

        return {
            "message": "Documento recebido com sucesso",
            "documento_id": novo_documento.id,
            "status": novo_documento.status_processamento
        }

    except IntegrityError:
        db.rollback()
        # Apaga o arquivo salvo localmente caso a inserção no banco falhe
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400, 
            detail="Erro de Integridade: Verifique se a inscricao_id, solicitado_id ou membro_id existem no banco de dados."
        )