from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    MEDIA_PATH: str = "/app/data/media"
    MAX_UPLOAD_MB: int = 10
    SITE_URL: str = "http://localhost"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
