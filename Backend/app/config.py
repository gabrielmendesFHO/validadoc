from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = BACKEND_ROOT / ".env" if (BACKEND_ROOT / ".env").exists() else (PROJECT_ROOT / ".env")

load_dotenv(ENV_FILE)

class Settings(BaseSettings):
    app_name: str = "ValidaDoc API"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/validadoc"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
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

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"

settings = Settings()
