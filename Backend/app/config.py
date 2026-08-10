from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

class Settings(BaseSettings):
    app_name: str = "ValidaDoc API"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/validadoc"
    gemini_api_key: str = ""
    # gemini-3.6-flash é o Flash GA atual (jul/2026). Fica configurável aqui
    # pra não precisar mexer em código quando o Google trocar de versão de novo.
    gemini_model: str = "gemini-3.6-flash"

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"

settings = Settings()
