from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel
import jwt
import logging
from app.config import settings
from app.repositories.user_repo import UserRepository

logger = logging.getLogger("staymatch.security")


_API_KEY = None


def get_api_key():
    global _API_KEY
    if _API_KEY is None:
        _API_KEY = settings.API_KEY
    return _API_KEY


def verify_api_key(x_api_key: str = Header(None)):
    expected = get_api_key()
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class CurrentUser(BaseModel):
    """Current authenticated user from JWT."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    token: Optional[str] = None


security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """
    Extract and validate JWT token from Authorization header.

    Automatically provisions user from .NET API if not found locally.

    Returns CurrentUser with user_id extracted from JWT claims.

    Raises HTTPException with 401 status if:
    - Token is missing
    - Token is invalid
    - Token is expired
    - Token signature is invalid
    - Required claims are missing
    """
    logger.info("GET_CURRENT_USER_ENTERED")

    if credentials is None:
        logger.error("NO_CREDENTIALS_RECEIVED")
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    logger.info(f"Credentials object: {credentials}")
    token = credentials.credentials
    logger.info(f"Authorization token received: {token[:30]}...")

    logger.info("STARTING_JWT_DECODE")
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        logger.info("JWT_DECODE_SUCCESS")
    except jwt.ExpiredSignatureError:
        logger.exception("JWT_DECODE_FAILED - Token expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.exception("JWT_DECODE_FAILED - Invalid token")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.exception("JWT_DECODE_FAILED - Validation error")
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    
    # Extract user_id from JWT claims
    # Try multiple possible claim names for user_id
    user_id = (
        payload.get("sub") or
        payload.get("user_id") or
        payload.get("userId") or
        payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
    )
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing required claim: user_id")
    
    logger.info(f"JWT User: {user_id}")
    
    # Extract optional claims
    email = payload.get("email") or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
    name = payload.get("name") or payload.get("unique_name") or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
    
    # Auto-provision user from .NET API if not found locally
    logger.info("Calling ensure_user_exists")
    try:
        user_repo = UserRepository(token=token)
        await user_repo.ensure_user_exists(str(user_id))
        user_repo.close()
        logger.info(f"Successfully provisioned user {user_id}")
    except Exception as e:
        logger.error(f"Failed to auto-provision user {user_id}: {e}")
        # Don't fail the request - user provisioning is best-effort
        # The request can continue even if provisioning fails
    
    return CurrentUser(
        user_id=str(user_id),
        email=email,
        name=name,
        token=token,
    )