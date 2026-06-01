from fastapi import APIRouter

from app.database.session import test_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }