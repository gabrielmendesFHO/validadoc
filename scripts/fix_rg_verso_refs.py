"""Reassocia documentos_enviados que apontam para RG_VERSO para o RG principal e deleta a entrada RG_VERSO.
"""
import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.db import SessionLocal
from app.models import DocumentosSolicitados, DocumentosEnviados

session = SessionLocal()
try:
    rg = session.query(DocumentosSolicitados).filter(DocumentosSolicitados.nome_documento == 'RG').one_or_none()
    rg_verso = session.query(DocumentosSolicitados).filter(DocumentosSolicitados.nome_documento.ilike('%verso%')).one_or_none()

    if not rg_verso:
        print('Nenhuma entrada RG_VERSO encontrada. Nada a fazer.')
        sys.exit(0)
    if not rg:
        print('Entrada RG principal nao encontrada. Abortando para evitar perda de referencial.')
        sys.exit(1)

    print(f'RG id={rg.id}, RG_VERSO id={rg_verso.id}')

    filhos = session.query(DocumentosEnviados).filter(DocumentosEnviados.solicitado_id == rg_verso.id).all()
    print(f'Encontrados {len(filhos)} documentos_enviados associados a RG_VERSO. Reassociando para RG id={rg.id}...')

    for f in filhos:
        print(f' - id documento enviado: {f.id}')
        f.solicitado_id = rg.id

    session.commit()
    print('Reassociação concluída. Removendo RG_VERSO...')

    session.delete(rg_verso)
    session.commit()
    print('Remoção concluída.')
finally:
    session.close()
