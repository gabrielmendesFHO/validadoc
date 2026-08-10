"""Remove entradas de 'RG verso' da tabela documentos_solicitados quando existirem.
Imprime o que será removido e confirma antes de deletar (executa automaticamente).
"""
import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.db import SessionLocal
from app.models import DocumentosSolicitados

session = SessionLocal()
try:
    candidatos = (
        session.query(DocumentosSolicitados)
        .filter(DocumentosSolicitados.nome_documento.ilike("%verso%"))
        .all()
    )
    if not candidatos:
        print("Nenhuma entrada com 'verso' encontrada em documentos_solicitados.")
        sys.exit(0)

    print("Entradas encontradas:")
    for c in candidatos:
        print(f"id={c.id}, nome_documento={c.nome_documento}")

    # Deleta
    for c in candidatos:
        print(f"Deletando id={c.id} nome_documento={c.nome_documento}...")
        session.delete(c)
    session.commit()
    print("Remoção concluída.")
finally:
    session.close()
