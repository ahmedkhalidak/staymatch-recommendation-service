from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.database.session import test_connection
from app.api.health import router as health_router
from app.api.router import router as main_router, tags_metadata
from app.core.security import security

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
    security=[{"HTTPBearer": []}],
)


# Configure OpenAPI security scheme for Bearer JWT authentication
app.openapi_security_schema = {
    "HTTPBearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
}


# Store original openapi method
_original_openapi = app.openapi


# Override OpenAPI to include custom security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = _original_openapi()
    openapi_schema["components"]["securitySchemes"] = app.openapi_security_schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Middleware to log incoming request headers for diagnostics
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_present = "Authorization" in request.headers
        logger.info(f"Request: {request.method} {request.url.path} - Authorization present: {auth_present}")
        if auth_present:
            auth_header = request.headers.get("Authorization", "")
            logger.info(f"Authorization header prefix: {auth_header[:20] if auth_header else 'empty'}...")
        response = await call_next(request)
        return response


app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router)
app.include_router(main_router)


# Custom 422 validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Override FastAPI's default validation error with custom ErrorResponse format."""
    # Extract first validation error for simplicity
    error_details = exc.errors()[0] if exc.errors() else {}
    field_name = str(error_details.get("loc", ["body"])[-1]) if error_details.get("loc") else "body"
    error_message = error_details.get("msg", "Validation error")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request body",
            "details": {
                "field": field_name,
                "reason": error_message
            }
        }
    )
