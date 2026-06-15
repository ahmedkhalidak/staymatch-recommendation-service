from fastapi import APIRouter

from app.database.session import test_connection
from app.schemas.recommendation import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check", description="Check if the API and database are healthy.", response_model=HealthCheckResponse, responses={
    200: {
        "description": "Health check successful",
        "content": {
            "application/json": {
                "example": {
                    "status": "healthy",
                    "database": "connected"
                }
            }
        }
    },
    503: {
        "description": "Service unavailable - database connection failed",
        "content": {
            "application/json": {
                "example": {
                    "status": "degraded",
                    "database": "disconnected"
                }
            }
        }
    }
})
def health_check():
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }