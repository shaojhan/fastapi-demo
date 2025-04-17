from functools import lru_cache
from typing import Literal
from os import path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FASTAPI_ENV: Literal['dev', 'staging']
    FASTAPI_TITLE: str
    
    SERVER_IP: str
    DATABASE_URL: str

    JWT_KEY: str

    SESSIONMIDDLEWARE_SECRET_KEY: str
    
    BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    # CELERY_ACCEPT_CONTENT: list
    
    model_config = SettingsConfigDict(env_file='.env', extra='allow')

settings = Settings()

@lru_cache
def get_settings(): return Settings()