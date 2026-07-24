from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "ValidaDoc API"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/validadoc"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
