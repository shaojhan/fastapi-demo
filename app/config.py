from functools import lru_cache
from typing import Literal
from os import path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     FASTAPI_ENV: Literal['dev', 'staging']
#     FASTAPI_TITLE: str
    
#     SERVER_IP: str
#     DATABASE_URL: str

#     JWT_KEY: str

#     SESSIONMIDDLEWARE_SECRET_KEY: str
    
#     BROKER_URL: str
#     CELERY_RESULT_BACKEND: str
#     # CELERY_ACCEPT_CONTENT: list
    
#     model_config = SettingsConfigDict(env_file='.env', extra='allow')

class BaseConfig(BaseSettings):
    FASTAPI_ENV: Literal['dev', 'test', 'prod']
    FASTAPI_TITLE: str
    DEBUG: bool = False
    
    SERVER_IP: str
    DATABASE_URL: str

    JWT_KEY: str

    SESSIONMIDDLEWARE_SECRET_KEY: str
    
    BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    # CELERY_ACCEPT_CONTENT: list
    CACHE_SERVER_HOST: str
    CACHE_SERVER_PORT: int
    
    model_config = SettingsConfigDict(env_file='.env', extra='allow')

# settings = Settings()

class DevConfig(BaseConfig):
    DEBUG: bool = True

class TestConfig(BaseConfig):
    pass

class ProdConfig(BaseConfig):
    pass

@lru_cache
def get_settings(): 
    env = os.getenv("ENV", "dev").lower()
    match env:
        case "dev": return DevConfig()
        case "test": return TestConfig()
        case "prod": return ProdConfig()
        case _: raise ValueError(f"Unknown ENV value: {env}")

    # return Settings()