from fastapi import Header, HTTPException
from app.config import Settings


_API_KEY = None


def get_api_key():
    global _API_KEY
    if _API_KEY is None:
        settings = Settings()
        _API_KEY = settings.api_key
    return _API_KEY


def verify_api_key(x_api_key: str = Header(None)):
    expected = get_api_key()
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")