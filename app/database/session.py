from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
import time
import logging
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs

from app.config import Settings

logger = logging.getLogger("staymatch.db")

_engine = None
_session_factory = None
_engine_failed = False


def _log_database_config(url: str):
    """Log database connection details and pool configuration."""
    parsed = urlparse(url)
    db_host = parsed.host
    db_port = parsed.port
    db_name = parsed.path.lstrip("/")
    sslmode = parse_qs(parsed.query).get("sslmode", [""])[0]
    logger.info(
        "DATABASE host=%s port=%s db=%s sslmode=%s | pool_pre_ping=True pool_recycle=300 pool_size=5 max_overflow=10",
        db_host, db_port, db_name, sslmode
    )


def get_engine():
    """Create or return the shared SQLAlchemy engine for Neon PostgreSQL."""
    global _engine, _engine_failed
    if _engine is None:
        settings = Settings()
        database_url = settings.database_url

        _log_database_config(database_url)

        try:
            _engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=5,
                max_overflow=10,
                pool_use_lifo=True,
                echo=False,
                connect_args={
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 3,
                }
            )

            @event.listens_for(_engine, "connect")
            def on_connect(dbapi_connection, connection_record):
                logger.debug("New DB connection established | pool=%s", _engine.pool.status() if _engine.pool else "n/a")

            @event.listens_for(_engine, "checkout")
            def on_checkout(dbapi_connection, connection_record, connection_proxy):
                logger.debug("DB connection checkout | pool=%s", _engine.pool.status() if _engine.pool else "n/a")

            @event.listens_for(_engine, "checkin")
            def on_checkin(dbapi_connection, connection_record):
                logger.debug("DB connection checkin | pool=%s", _engine.pool.status() if _engine.pool else "n/a")

            _wait_for_db(_engine)
            _engine_failed = False
        except Exception as e:
            _engine_failed = True
            logger.error("FATAL: Could not create database engine: %s", e)
            raise
    return _engine


def _wait_for_db(engine, retries=5, delay=2):
    """Verify database connectivity with retries and detailed logging."""
    for attempt in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status = engine.pool.status() if engine.pool else "n/a"
            logger.info("Database connection verified on attempt %d/%d | pool=%s", attempt + 1, retries, status)
            return
        except OperationalError as e:
            status = engine.pool.status() if engine.pool else "n/a"
            if attempt < retries - 1:
                logger.warning(
                    "DB not ready (attempt %d/%d): %s | pool=%s",
                    attempt + 1, retries, str(e), status
                )
                time.sleep(delay * (attempt + 1))
            else:
                logger.error(
                    "DB connection failed after %d attempts: %s | pool=%s",
                    retries, str(e), status
                )
                raise


def get_session():
    """Return a new scoped session from the engine."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    return _session_factory()


def retry_on_connection_error(func, max_retries=3, delay=1):
    """Retry function on connection errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if "SSL connection has been closed unexpectedly" in str(e) or "connection closed" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning("Connection error (attempt %d/%d), retrying...", attempt + 1, max_retries)
                    time.sleep(delay * (2 ** attempt))
                else:
                    logger.error("Connection failed after %d attempts: %s", max_retries, e)
                    raise
            else:
                raise
    return None


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
        logger.info("Manual DB connection test passed | pool=%s", engine.pool.status())
        return True
    except Exception:
        logger.error("Manual DB connection test failed")
        return False


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
