from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import time
import logging

from app.config import Settings

logger = logging.getLogger("staymatch.db")

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = Settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        _wait_for_db(_engine)
    return _engine


def _wait_for_db(engine, retries=5, delay=2):
    for attempt in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as e:
            if attempt < retries - 1:
                logger.warning("DB not ready (attempt %d/%d): %s", attempt + 1, retries, e)
                time.sleep(delay * (attempt + 1))
            else:
                logger.error("DB connection failed after %d attempts: %s", retries, e)
                raise


def get_session():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    return _session_factory()


def get_mssql_engine():
    """Create MSSQL engine using FreeTDS (same driver as chatbot)."""
    settings = Settings()
    if not settings.mssql_connection_string and not all(
        [settings.db_host, settings.db_port, settings.db_name, settings.db_user]
    ):
        logger.warning("No MSSQL connection configured — sync disabled")
        return None

    if settings.mssql_connection_string:
        conn_str = settings.mssql_connection_string
    else:
        from urllib.parse import quote_plus
        encoded_password = quote_plus(settings.db_password)
        conn_str = (
            f"mssql+pyodbc://{settings.db_user}:{encoded_password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
            f"?driver=FreeTDS&TDS_Version=8.0&Encrypt=no"
        )

    try:
        engine = create_engine(
            conn_str,
            pool_pre_ping=True,
            echo=False,
            connect_args={"trustservercertificate": "yes"}
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MSSQL connection established")
        return engine
    except Exception as e:
        logger.error("Failed to connect to MSSQL: %s", e)
        return None


def test_connection():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
