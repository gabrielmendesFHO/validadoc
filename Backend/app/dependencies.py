"""Dependências de autenticação/autorização reutilizáveis nas rotas."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Inscricoes, StatusJornada, Usuarios
from .security import decodificar_access_token

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Ordem de progressão da jornada do candidato (menor = mais inicial)
_ORDEM_JORNADA: dict[StatusJornada, int] = {
    StatusJornada.PRE_CADASTRADO:   0,
    StatusJornada.KYC_PENDENTE:     1,
    StatusJornada.KYC_VALIDADO:     2,
    StatusJornada.FAMILIA_PENDENTE: 3,
    StatusJornada.DOCS_PENDENTES:   4,
    StatusJornada.PRONTO_AUDITORIA: 5,
    StatusJornada.CONCLUIDO:        6,
    StatusJornada.ABANDONO:         99,
}


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

    try:
        usuario = db.get(Usuarios, int(usuario_id))
    except (TypeError, ValueError):
        raise credenciais_invalidas
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


def validar_status_funil(inscricao: Inscricoes, status_minimo: StatusJornada, usuario: Usuarios):
    """Valida se o status_funil da inscrição atinge o nível mínimo exigido para o candidato."""
    if usuario.perfil in {"ANALISTA", "ADMIN"}:
        return

    if inscricao.status_funil == StatusJornada.ABANDONO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta inscrição foi abandonada e não pode avançar nas etapas.",
        )

    nivel_minimo = _ORDEM_JORNADA.get(status_minimo, 0)
    status_atual = inscricao.status_funil
    nivel_atual = _ORDEM_JORNADA.get(status_atual, 0)

    if nivel_atual < nivel_minimo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Ação bloqueada. Seu status atual é '{status_atual}'. "
                f"É necessário concluir a etapa de '{status_minimo.value}' antes de continuar."
            ),
        )


def exigir_jornada_minima(status_minimo: StatusJornada):
    """Bloqueia o CANDIDATO de acessar a rota caso seu status_funil seja inferior ao mínimo exigido.

    Analistas e ADMINs sempre passam (supervisão).

    Uso:
        @router.post("/{inscricao_id}/membros")
        def adicionar_membro(
            inscricao_id: int,
            db: Session = Depends(get_db),
            usuario: Usuarios = Depends(exigir_jornada_minima(StatusJornada.KYC_PENDENTE)),
        ): ...
    """
    def _checar(
        inscricao_id: int,
        usuario: Usuarios = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Usuarios:
        if usuario.perfil in {"ANALISTA", "ADMIN"}:
            return usuario

        inscricao = db.get(Inscricoes, inscricao_id)
        if inscricao is None:
            raise HTTPException(status_code=404, detail="Inscrição não encontrada.")
        if inscricao.candidato_id != usuario.id:
            raise HTTPException(status_code=403, detail="Você não tem acesso a esta inscrição.")

        validar_status_funil(inscricao, status_minimo, usuario)
        return usuario

    return _checar


def usuario_pode_acessar_inscricao(usuario: Usuarios, inscricao) -> bool:
    """Candidatos acessam a própria inscrição; equipe acessa as inscrições."""
    if usuario.perfil in {"ANALISTA", "ADMIN"}:
        return True
    return usuario.id == inscricao.candidato_id
