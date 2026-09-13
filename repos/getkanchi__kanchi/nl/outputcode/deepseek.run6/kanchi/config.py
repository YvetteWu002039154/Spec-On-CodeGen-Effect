import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kanchi.db"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    ORPHAN_TIMEOUT_SECONDS: int = 60
    EVENT_QUEUE_MAXSIZE: int = 1000
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()

