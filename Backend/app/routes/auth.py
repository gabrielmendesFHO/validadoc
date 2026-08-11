from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Usuarios
from ..security import criar_access_token, hash_senha, verificar_senha

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class RegistroIn(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: str
    cpf: str | None = None


@router.post("/registrar", status_code=status.HTTP_201_CREATED)
def registrar(dados: RegistroIn, db: Session = Depends(get_db)):
    existente = db.query(Usuarios).filter_by(email=dados.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    novo_usuario = Usuarios(
        nome_completo=dados.nome_completo,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        perfil="CANDIDATO",
        cpf=dados.cpf,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id, "email": novo_usuario.email}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuarios).filter_by(email=form.username).first()
    if usuario is None or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    token = criar_access_token({"sub": str(usuario.id), "perfil": usuario.perfil})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome_completo": usuario.nome_completo,
            "email": usuario.email,
            "perfil": usuario.perfil,
        },
    }


@router.get("/eu")
def eu(usuario: Usuarios = Depends(get_current_user)):
    return {
        "id": usuario.id,
        "nome_completo": usuario.nome_completo,
        "email": usuario.email,
        "perfil": usuario.perfil,
    }