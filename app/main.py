from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.router import router as main_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="StayMatch Recommendation Service",
    description="Property recommendation, room recommendation, and roommate matching engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(main_router)