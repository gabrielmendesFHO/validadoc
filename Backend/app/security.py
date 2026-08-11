"""Hashing de senha e geração/validação de tokens JWT.

Usa pwdlib em vez de passlib: o passlib está sem manutenção há anos e quebra
com versões recentes do pacote bcrypt (erro "module 'bcrypt' has no
attribute '__about__'" / ValueError de 72 bytes ao chamar verify/hash). O
pwdlib é o substituto hoje recomendado pela própria documentação oficial do
FastAPI.

Argon2 é o algoritmo usado para hashes NOVOS (mais forte, é o padrão atual
recomendado pela OWASP). O BcryptHasher fica registrado só pra continuar
validando os hashes antigos que já estão no banco (ex.: o do seed), sem
precisar recriar nenhum usuário.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from .config import settings

_password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))


def hash_senha(senha: str) -> str:
    return _password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return _password_hash.verify(senha, senha_hash)


def criar_access_token(dados: dict, expira_em: Optional[timedelta] = None) -> str:
    payload = dados.copy()
    expira = datetime.now(timezone.utc) + (expira_em or timedelta(minutes=settings.jwt_expira_minutos))
    payload["exp"] = expira
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decodificar_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError(f"Token inválido: {exc}") from exc