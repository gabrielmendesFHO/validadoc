from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Inscricoes, MembrosFamilia

router = APIRouter(prefix="/inscricoes", tags=["Inscrições"])


class MembroFamiliaIn(BaseModel):
    nome_completo: str
    parentesco: str | None = None
    renda_declarada: float | None = None


@router.post("/{inscricao_id}/membros")
def adicionar_membro(inscricao_id: int, membro: MembroFamiliaIn, db: Session = Depends(get_db)):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")

    novo_membro = MembrosFamilia(inscricao_id=inscricao_id, **membro.model_dump())
    db.add(novo_membro)
    db.commit()
    db.refresh(novo_membro)
    return novo_membro


@router.get("/{inscricao_id}/membros")
def listar_membros(inscricao_id: int, db: Session = Depends(get_db)):
    inscricao = db.get(Inscricoes, inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
    return inscricao.membros_familia