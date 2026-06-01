from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import Settings


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
    return _engine


def get_session():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    return _session_factory()


def get_mssql_engine():
    settings = Settings()
    if not settings.mssql_connection_string:
        return None
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={settings.mssql_connection_string}",
        pool_pre_ping=True,
        echo=False
    )


def test_connection():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False