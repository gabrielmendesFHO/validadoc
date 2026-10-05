from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import load_dotenv
from cryptography.fernet import Fernet
from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = BACKEND_ROOT / ".env" if (BACKEND_ROOT / ".env").exists() else (PROJECT_ROOT / ".env")

load_dotenv(ENV_FILE)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", hide_input_in_errors=True, extra="ignore")
    app_env: Literal["development", "homologation"] = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    smtp_enabled: bool = True
    app_name: str = "ValidaDoc API"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/validadoc"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_fallback_model: str = "gemini-flash-lite-latest"
    gemini_timeout_ms: int = 45000
    jwt_secret_key: str = "troque-essa-chave-no-.env"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 480  # 8h
    encryption_key: str = ""

    # Configurações de E-mail (SMTP)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@validadoc.com.br"

    @field_validator("cors_origins")
    @classmethod
    def validar_origens(cls, value, info: ValidationInfo):
        if info.data.get("app_env") == "homologation":
            if not value:
                raise ValueError("cors_origins exige origens HTTPS explícitas")
            for origin in value:
                try:
                    url = urlsplit(origin)
                    valid = (url.scheme == "https" and url.hostname and url.hostname not in {"localhost", "127.0.0.1", "::1"}
                             and not url.username and not url.password and not url.query and not url.fragment
                             and not url.path and "*" not in origin and url.port != 0)
                except ValueError:
                    valid = False
                if not valid:
                    raise ValueError("cors_origins deve conter somente origens HTTPS públicas, sem caminho")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validar_jwt(cls, value, info: ValidationInfo):
        if info.data.get("app_env") == "homologation" and (len(value.strip()) < 32 or value == "troque-essa-chave-no-.env"):
            raise ValueError("jwt_secret_key deve ser própria e ter pelo menos 32 caracteres")
        return value

    @field_validator("encryption_key")
    @classmethod
    def validar_criptografia(cls, value, info: ValidationInfo):
        if info.data.get("app_env") == "homologation":
            try:
                Fernet(value.encode())
            except (ValueError, TypeError):
                raise ValueError("encryption_key deve ser uma chave Fernet válida") from None
        return value

settings = Settings()
