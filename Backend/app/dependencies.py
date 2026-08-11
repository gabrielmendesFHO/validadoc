"""Dependências de autenticação/autorização reutilizáveis nas rotas."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Usuarios
from .security import decodificar_access_token

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(_oauth2_scheme), db: Session = Depends(get_db)) -> Usuarios:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodificar_access_token(token)
    except ValueError:
        raise credenciais_invalidas

    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise credenciais_invalidas

    usuario = db.get(Usuarios, int(usuario_id))
    if usuario is None:
        raise credenciais_invalidas

    return usuario


def exigir_perfil(*perfis_permitidos: str):
    """Ex.: Depends(exigir_perfil("ANALISTA", "ADMIN"))"""

    def _checar(usuario: Usuarios = Depends(get_current_user)) -> Usuarios:
        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Ação restrita a perfis: {', '.join(perfis_permitidos)}.",
            )
        return usuario

    return _checar