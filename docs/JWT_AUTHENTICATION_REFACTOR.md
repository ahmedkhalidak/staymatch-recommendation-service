# JWT Authentication Refactor Documentation

## Overview

This document describes the JWT authentication refactor implemented for the StayMatch Recommendation Service. The refactor removes user_id from API routes and instead extracts the authenticated user from JWT tokens issued by the .NET Authentication Service.

## Goals

- Stop accepting user_id in API routes
- Extract current authenticated user from JWT token
- Align with production-ready architecture
- Support Flutter app consumption pattern
- Enable Swagger authorization testing

## Implementation Details

### Configuration

Added JWT configuration to `app/config.py`:

```python
JWT_SECRET: str = ""
JWT_ISSUER: str = ""
JWT_AUDIENCE: str = ""
```

These values are read from environment variables:
- `JWT_SECRET` - Secret key for JWT signature validation
- `JWT_ISSUER` - Expected JWT issuer
- `JWT_AUDIENCE` - Expected JWT audience

### Authentication Dependency

Created `get_current_user()` FastAPI dependency in `app/core/security.py`:

```python
class CurrentUser(BaseModel):
    """Current authenticated user from JWT."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Extract and validate JWT token from Authorization header."""
```

**Features:**
- Reads Authorization header with Bearer token
- Validates JWT signature, issuer, audience, and expiration
- Extracts user_id from multiple possible claim names:
  - `sub` (priority)
  - `user_id`
  - `userId`
  - `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier`
- Extracts optional email and name claims
- Returns 401 Unauthorized for:
  - Missing token
  - Invalid token
  - Expired token
  - Invalid signature
  - Missing required claims

### FastAPI Security Integration

Added security scheme to `app/main.py`:

```python
from app.core.security import security

app = FastAPI(
    title="StayMatch Recommendation Service",
    description="Roommate matching and questionnaire management",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    security=[{"Bearer": []}],  # Added security scheme
)
```

This enables the "Authorize" button in Swagger UI.

### Endpoint Refactoring

All user-specific endpoints were refactored to remove user_id from routes and use JWT authentication.

#### Before/After Endpoint List

| Before | After | Method |
|--------|-------|--------|
| `GET /profile/questionnaire/{user_id}` | `GET /profile/questionnaire` | Removed user_id parameter |
| `GET /questionnaire/status/{user_id}` | `GET /questionnaire/status` | Removed user_id parameter |
| `POST /questionnaire/answers/{user_id}` | `POST /questionnaire/answers` | Removed user_id parameter |
| `GET /match/property/{user_id}/{property_id}` | `GET /match/property/{property_id}` | Removed user_id parameter |
| `POST /match/shared-properties/{user_id}` | `POST /match/shared-properties` | Removed user_id parameter |

#### Implementation Pattern

**Before:**
```python
@router.get("/profile/questionnaire/{user_id}")
async def get_profile_questionnaire(user_id: str):
    return await profile_questionnaire_service.get_profile_questionnaire(user_id)
```

**After:**
```python
@router.get("/profile/questionnaire")
async def get_profile_questionnaire(current_user: get_current_user = Depends(get_current_user)):
    return await profile_questionnaire_service.get_profile_questionnaire(current_user.user_id)
```

### Service Layer

**No changes required.** Service layer methods continue to accept `user_id` as a parameter. The router is responsible for extracting the user_id from JWT and passing it to the service. This maintains proper separation of concerns.

### Database Layer

**No changes required.** The database architecture remains unchanged. Repositories continue to resolve `external_user_id` to `user_profile_id` internally.

## Testing

### Unit Tests

Created comprehensive unit tests in `tests/test_jwt_auth.py`:

- ✅ Valid token validation
- ✅ Token with XML SOAP nameidentifier claim
- ✅ Expired token handling
- ✅ Invalid signature handling
- ✅ Missing user_id claim handling
- ✅ Wrong issuer handling
- ✅ Wrong audience handling
- ✅ Optional claims missing
- ✅ User ID claim priority
- ✅ Fallback to alternative user_id claims

All 10 tests pass.

### Swagger Testing

To test with Swagger UI:

1. Login using .NET Swagger to get JWT token
2. Open Recommendation Service Swagger UI at `http://localhost:8000/docs`
3. Click "Authorize" button
4. Paste JWT token with `Bearer ` prefix: `Bearer eyJ...`
5. Execute endpoints
6. User is automatically identified from JWT

### Manual Testing

To test manually with curl:

```bash
# Get JWT from .NET API first
JWT_TOKEN="your-jwt-token-here"

# Test profile questionnaire endpoint
curl -X GET http://localhost:8000/profile/questionnaire \
  -H "Authorization: Bearer $JWT_TOKEN"

# Test questionnaire status endpoint
curl -X GET http://localhost:8000/questionnaire/status \
  -H "Authorization: Bearer $JWT_TOKEN"

# Test questionnaire answers submission
curl -X POST http://localhost:8000/questionnaire/answers \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"age_group": 1, "occupation_status": 2}'
```

## Error Handling

All authentication errors return `401 Unauthorized`:

- Missing authorization header
- Invalid token
- Expired token
- Invalid signature
- Missing required claim (user_id)
- Wrong issuer
- Wrong audience

## Dependencies

Added to `requirements.txt`:
```
PyJWT==2.8.0
```

## Environment Variables

Add to `.env` file:

```env
# JWT Authentication Configuration
JWT_SECRET=your-jwt-secret-key
JWT_ISSUER=your-jwt-issuer
JWT_AUDIENCE=your-jwt-audience
```

## Security Considerations

- JWT validation is enabled and enforced
- Signature validation is required (unsigned tokens are rejected)
- Expiration validation is enforced
- Issuer and audience validation is enforced
- No authentication bypass mechanisms
- All protected endpoints require valid JWT

## Migration Notes

### For Flutter App

**Before:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/profile/questionnaire/$userId'),
  headers: {'Authorization': 'Bearer $token'},
);
```

**After:**
```dart
final response = await http.get(
  Uri.parse('$baseUrl/profile/questionnaire'),
  headers: {'Authorization': 'Bearer $token'},
);
```

The user_id is no longer needed in the URL - it's extracted from the JWT token.

### For Admin Endpoints

Admin endpoints were NOT refactored and still use user_id parameters:
- `GET /admin/questionnaire/questions` (no change)
- `GET /admin/questionnaire/users` (no change)
- `GET /admin/questionnaire/answers/{user_id}` (no change)
- `POST /admin/questionnaire/answers/{user_id}` (no change)
- `DELETE /admin/questionnaire/answers/{user_id}` (no change)

These endpoints are intended for administrative use and may require different authentication mechanisms.

## Summary

This refactor successfully:
- ✅ Removed user_id from all user-facing API routes
- ✅ Implemented JWT authentication with full validation
- ✅ Added Swagger authorization support
- ✅ Maintained database architecture unchanged
- ✅ Maintained service layer unchanged
- ✅ Added comprehensive unit tests
- ✅ Provided clear error handling
- ✅ Documented all changes

The implementation is production-ready and aligns with modern authentication best practices.
