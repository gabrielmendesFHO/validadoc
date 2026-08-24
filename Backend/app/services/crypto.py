"""Criptografia simétrica para o conteúdo dos documentos armazenados no banco.

Usa Fernet (da própria lib `cryptography`, já dependência transitiva via
python-jose[cryptography]) — criptografia autenticada, simples de operar com
uma chave só. A chave NUNCA vai pro banco nem pro repositório: fica só no
.env, igual o JWT_SECRET_KEY.
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


class CriptografiaNaoConfiguradaError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    if not settings.encryption_key:
        raise CriptografiaNaoConfiguradaError(
            "ENCRYPTION_KEY não configurada. Gere uma com:\n"
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(settings.encryption_key.encode())


def criptografar(conteudo: bytes) -> bytes:
    return _get_fernet().encrypt(conteudo)


def descriptografar(conteudo: bytes) -> bytes:
    try:
        return _get_fernet().decrypt(conteudo)
    except InvalidToken as exc:
        raise ValueError(
            "Não foi possível descriptografar o arquivo (chave incorreta ou dado corrompido)."
        ) from exc