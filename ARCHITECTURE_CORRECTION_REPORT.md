# Architecture Correction Report

## Summary

Applied critical corrections to the schema simplification based on architectural review. The database now uses `user_profile_id` internally while the public API continues to use external `user_id` (.NET user ID), maintaining clean separation between external interfaces and internal database structure.

## Issues Identified

### 1. Naming Inconsistency
**Problem:** `questionnaire_profiles.user_id` was named differently from other questionnaire tables which use `user_profile_id`.

**Solution:** Renamed `questionnaire_profiles.user_id` to `user_profile_id` for consistency across all questionnaire-related tables.

### 2. API Breaking Change
**Problem:** Changed public API endpoints to use `user_profile_id` instead of external `user_id`, which would require frontend changes and expose internal database details.

**Solution:** Restored all API routes to use external `user_id` (which maps to `user_profiles.external_user_id`). Repositories and services now handle the conversion internally.

## Corrections Applied

### ORM Model Updates

**questionnaire_profiles**
```python
# Before
user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, unique=True)

# After
user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, unique=True)
```

### Repository Updates

**questionnaire_repo.py**
- Added `_resolve_user_profile_id(external_user_id: str)` helper method
- Updated `save_answers(external_user_id: str, ...)` to resolve external user ID
- Updated `get_answers(external_user_id: str)` to resolve external user ID
- Updated `get_questionnaire_status(external_user_id: str)` to resolve external user ID
- All methods now return `user_id` (external) in responses instead of `user_profile_id`

### API Route Updates

**router.py**
- `POST /questionnaire/answers/{user_id}` - Restored to use external user ID
- `GET /questionnaire/status/{user_id}` - Restored to use external user ID
- `GET /admin/questionnaire/answers/{user_id}` - Restored to use external user ID
- `POST /admin/questionnaire/answers/{user_id}` - Restored to use external user ID
- `DELETE /admin/questionnaire/answers/{user_id}` - Restored to use external user ID with internal resolution
- `GET /admin/questionnaire/users` - Returns both `user_profile_id` and `external_user_id` for lookup

### Matching Engine

**compatibility_engine.py**
- Already had `_get_user_profile_id(external_user_id: str)` method (no changes needed)
- All matching methods accept external user IDs and convert internally
- No changes required - architecture was already correct

### Migration Files Created

**015_rename_questionnaire_profiles_user_id.py**
- Renames `questionnaire_profiles.user_id` to `user_profile_id`
- Updates index for consistency
- Provides downgrade path

## Final Architecture

### External API (Public Interface)
- Uses `user_id` which maps to `user_profiles.external_user_id`
- Frontend and external services only know the .NET user ID
- No exposure of internal database structure

### Database (Internal Structure)
- All questionnaire tables use `user_profile_id` (UUID FK → user_profiles.id)
- Single source of truth: `user_profiles.id`
- External user ID only exists in `user_profiles.external_user_id`

### Internal Conversion
- Repositories/services resolve `external_user_id` → `user_profile_id`
- Matching engine resolves `external_user_id` → `user_profile_id`
- Conversion happens transparently to API consumers

## Verification Results

### Column Naming Consistency
- ✅ `questionnaire_profiles.user_profile_id` (renamed from `user_id`)
- ✅ `user_questionnaire_answers.user_profile_id`
- ✅ `user_search_preferences.user_profile_id`
- ✅ All questionnaire tables now use consistent naming

### Foreign Key Verification
- ✅ `questionnaire_profiles.user_profile_id` → `user_profiles.id`
- ✅ `user_questionnaire_answers.user_profile_id` → `user_profiles.id`
- ✅ `user_search_preferences.user_profile_id` → `user_profiles.id`
- ✅ All foreign keys point to `user_profiles.id`

### API Verification
- ✅ Questionnaire repository accepts external user IDs
- ✅ Questionnaire repository resolves to user_profile_id internally
- ✅ API responses return `user_id` (external) not `user_profile_id`
- ✅ Admin endpoints work with external user IDs

### Matching Engine Verification
- ✅ Matching engine accepts external user IDs (seeker_id, occ_user_id)
- ✅ Matching engine converts to user_profile_id internally
- ✅ Matching engine uses user_profile_id for database operations
- ✅ No changes required - architecture was already correct

## API Routes Summary

### Questionnaire Endpoints
```
POST /questionnaire/answers/{user_id}
GET /questionnaire/status/{user_id}
GET /questionnaire/questions
```

### Admin Endpoints
```
GET /admin/questionnaire/users
GET /admin/questionnaire/answers/{user_id}
POST /admin/questionnaire/answers/{user_id}
DELETE /admin/questionnaire/answers/{user_id}
GET /admin/questionnaire/questions
```

### Matching Endpoints
```
GET /match/property/{user_id}/{property_id}
POST /match/shared-properties/{user_id}
```

**Note:** All `{user_id}` parameters refer to external user IDs (user_profiles.external_user_id), not internal user_profile_id.

## Database Schema Summary

### user_profiles (ROOT ENTITY)
```
id: UUID (PK)
external_user_id: VARCHAR (UNIQUE) - External .NET user ID
auth_user_id: UUID
full_name: TEXT
phone: VARCHAR(50)
gender: VARCHAR(20)
birth_year: INTEGER
nationality: VARCHAR(100)
occupation: VARCHAR(100)
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

### questionnaire_profiles
```
id: SERIAL (PK)
user_profile_id: UUID (FK → user_profiles.id, UNIQUE)
completion_percentage: INTEGER
last_answered_at: TIMESTAMP
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

### user_questionnaire_answers
```
id: SERIAL (PK)
user_profile_id: UUID (FK → user_profiles.id, NOT NULL)
question_id: INTEGER (FK → questionnaire_questions.id, NOT NULL)
answer_value: TEXT
answer_scale: INTEGER
answered_at: TIMESTAMP
```

### user_search_preferences
```
id: SERIAL (PK)
user_profile_id: UUID (FK → user_profiles.id, NOT NULL, UNIQUE)
min_budget: INTEGER
max_budget: INTEGER
preferred_city: TEXT
preferred_government: TEXT
preferred_property_type: VARCHAR(20)
furnished: BOOLEAN
wifi: BOOLEAN
air_conditioning: BOOLEAN
balcony: BOOLEAN
private_bathroom: BOOLEAN
tenant_type: VARCHAR(20)
gender_preference: VARCHAR(20)
shared_room: BOOLEAN
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

## Benefits of Corrected Architecture

### 1. Clean Separation of Concerns
- External API uses stable external user IDs
- Database uses optimized internal foreign keys
- Conversion layer handles the mapping transparently

### 2. No Frontend Changes Required
- Frontend continues to use .NET user IDs
- No need to fetch or store internal user_profile_id
- No breaking changes for existing integrations

### 3. Consistent Naming
- All questionnaire tables use `user_profile_id`
- No confusion about which ID to use where
- Clear distinction between external and internal IDs

### 4. Maintainable Code
- Single responsibility: repositories handle ID resolution
- Easy to understand data flow
- Clear separation between layers

## Migration Path

Since there is no production data:
- ✅ All development data was truncated before changes
- ✅ No data migration was needed
- ✅ Clean slate with corrected architecture

## Conclusion

The architecture has been corrected to follow best practices:
- **External API**: Uses stable external user IDs
- **Database**: Uses optimized internal foreign keys
- **Conversion**: Handled transparently in repositories/services
- **Frontend**: No changes required, continues using external user IDs

This provides a clean, maintainable architecture that separates external interfaces from internal database structure while maintaining data integrity and consistency.
