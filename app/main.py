from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.database.session import test_connection
from app.api.health import router as health_router
from app.api.router import router as main_router
from app.services.preferences_bridge import PreferencesBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staymatch")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting StayMatch Recommendation Service...")
    db_ok = test_connection()
    if db_ok:
        logger.info("Database connection verified")
        bridge = PreferencesBridge()
        result = bridge.sync_all()
        logger.info("Preferences bridge synced: %s", result)
    else:
        logger.warning("Database connection failed on startup — check DATABASE_URL")
    yield
    logger.info("Shutting down StayMatch Recommendation Service...")


app = FastAPI(
    title="StayMatch Recommendation Service",
    description="Property recommendation, room recommendation, and roommate matching engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(main_router)
