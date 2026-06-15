from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.database.session import test_connection
from app.api.health import router as health_router
from app.api.router import router as main_router, tags_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staymatch")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting StayMatch Recommendation Service...")
    db_ok = test_connection()
    if db_ok:
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection failed on startup — check DATABASE_URL")
    yield
    logger.info("Shutting down StayMatch Recommendation Service...")


app = FastAPI(
    title="StayMatch Recommendation Service",
    description="Roommate matching and questionnaire management",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

app.include_router(health_router)
app.include_router(main_router)
