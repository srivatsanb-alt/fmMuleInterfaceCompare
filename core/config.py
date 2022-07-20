import secrets
from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    FM_SECRET_KEY: str = secrets.token_urlsafe(32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    FM_DATABASE_URI: PostgresDsn

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
