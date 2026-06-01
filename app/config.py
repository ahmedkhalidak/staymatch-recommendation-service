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

    sync_interval_minutes: int = 5
    api_key: str = ""
    scoring_weights_override: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
