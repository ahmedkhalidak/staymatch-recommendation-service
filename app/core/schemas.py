"""Common schemas for API responses."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ErrorResponse(BaseModel):
    """Standard error response for all API endpoints."""
    error: str = Field(..., description="Error type identifier (e.g., 'validation_error', 'not_found', 'unauthorized')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details (e.g., field-specific validation errors)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "validation_error",
                    "message": "Invalid request body",
                    "details": {
                        "field": "age_group",
                        "reason": "Value must be between 1 and 4"
                    }
                },
                {
                    "error": "not_found",
                    "message": "User profile not found"
                },
                {
                    "error": "unauthorized",
                    "message": "Authentication required"
                },
                {
                    "error": "internal_error",
                    "message": "Unexpected server error"
                }
            ]
        }
    }
