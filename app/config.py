from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    mssql_connection_string: str = ""

    # Fallback MSSQL connection fields (matching chatbot pattern)
    db_host: str = ""
    db_port: int = 1433
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""

    # .NET Property API configuration
    PROPERTY_API_BASE_URL: str = ""
    PROPERTY_API_TOKEN: str = ""  # JWT token for API authentication

    # JWT Authentication configuration
    JWT_SECRET: str = ""
    JWT_ISSUER: str = ""
    JWT_AUDIENCE: str = ""

    sync_interval_minutes: int = 5
    API_KEY: str = ""
    scoring_weights_override: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
settings = Settings()
