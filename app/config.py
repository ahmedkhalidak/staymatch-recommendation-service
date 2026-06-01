from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    mssql_connection_string: str = ""
    sync_interval_minutes: int = 5
    scoring_weights_override: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"