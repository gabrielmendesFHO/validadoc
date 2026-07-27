from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "ValidaDoc API"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/validadoc"
    gemini_api_key: str = ""
    # gemini-3.6-flash é o Flash GA atual (jul/2026). Fica configurável aqui
    # pra não precisar mexer em código quando o Google trocar de versão de novo.
    gemini_model: str = "gemini-3.6-flash"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
