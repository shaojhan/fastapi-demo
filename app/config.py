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

    # Email / SMTP
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # Google Calendar
    GOOGLE_CALENDAR_API_BASE: str = "https://www.googleapis.com/calendar/v3"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_CALENDAR_REDIRECT_URI: str = "http://localhost:8000/api/schedules/google/callback"
    GOOGLE_CALENDAR_SCOPES: str = "https://www.googleapis.com/auth/calendar"

    # SSO
    SSO_STATE_SECRET: str = "change-me-in-production"
    SSO_CALLBACK_BASE_URL: str = "http://localhost:8000/api"

    # S3 / MinIO
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "avatars"
    S3_PUBLIC_URL: str = "http://localhost:9000"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "fastapi-demo"
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_KEEPALIVE: int = 60

    # Verification
    FRONTEND_URL: str = "http://localhost"
    VERIFICATION_TOKEN_EXPIRY_SECONDS: int = 86400
    PASSWORD_RESET_TOKEN_EXPIRY_SECONDS: int = 3600
    
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