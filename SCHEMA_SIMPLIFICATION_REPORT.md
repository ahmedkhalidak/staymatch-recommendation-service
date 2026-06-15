# Schema Simplification Report

## Summary

Successfully removed legacy `user_id` columns from questionnaire-related tables and established `user_profiles` as the single root entity. All questionnaire tables now reference `user_profiles.id` via foreign keys only.

## Changes Made

### Columns Removed

**user_questionnaire_answers**
- Removed: `user_id` (String)
- Remaining: `user_profile_id` (UUID, FK → user_profiles.id, NOT NULL)

**user_search_preferences**
- Removed: `user_id` (String, UNIQUE)
- Remaining: `user_profile_id` (UUID, FK → user_profiles.id, NOT NULL, UNIQUE)

### ORM Models Updated

**UserQuestionnaireAnswer**
```python
# Before
user_id = Column(String(255), nullable=False)
user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=True)

# After
user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)
```

**UserSearchPreference**
```python
# Before
user_id = Column(String(255), nullable=False, unique=True)
user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=True)

# After
user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, unique=True)
```

### Repository Updates

**questionnaire_repo.py**
- `save_answers(user_id: str)` → `save_answers(user_profile_id: str)`
- `get_answers(user_id: str)` → `get_answers(user_profile_id: str)`
- `get_questionnaire_status(user_id: str)` → `get_questionnaire_status(user_profile_id: str)`
- All queries updated to use `user_profile_id` instead of `user_id`

### API Endpoints Updated

**router.py**
- `POST /questionnaire/answers/{user_id}` → `POST /questionnaire/answers/{user_profile_id}`
- `GET /questionnaire/status/{user_id}` → `GET /questionnaire/status/{user_profile_id}`
- `GET /admin/questionnaire/answers/{user_id}` → `GET /admin/questionnaire/answers/{user_profile_id}`
- `POST /admin/questionnaire/answers/{user_id}` → `POST /admin/questionnaire/answers/{user_profile_id}`
- `DELETE /admin/questionnaire/answers/{user_id}` → `DELETE /admin/questionnaire/answers/{user_profile_id}`
- `GET /admin/questionnaire/users` - Updated to join with UserProfile and return both `user_profile_id` and `external_user_id`

### Matching Engine Updates

**compatibility_engine.py**
- Added `_get_user_profile_id(external_user_id: str)` helper method to convert external user IDs to user_profile_ids
- Updated `_get_answers_as_dict(user_profile_id: str)` to use `user_profile_id`
- Updated all matching methods to convert external user IDs to user_profile_ids before querying questionnaire answers
- Maintains compatibility with .NET API external user IDs while using internal user_profile_id for database operations

### Migration Files Created

**014_remove_legacy_user_id_columns.py**
- Drops dependent view `questionnaire_profiles_view`
- Drops `user_id` column from `user_questionnaire_answers`
- Drops `user_id` column from `user_search_preferences`
- Makes `user_profile_id` NOT NULL in both tables
- Makes `user_profile_id` UNIQUE in `user_search_preferences`

## Final ERD Structure

```
user_profiles (ROOT ENTITY)
├── id: UUID (PK)
├── external_user_id: VARCHAR (UNIQUE) - External .NET user ID
├── auth_user_id: UUID
├── full_name: TEXT
├── phone: VARCHAR(50)
├── gender: VARCHAR(20)
├── birth_year: INTEGER
├── nationality: VARCHAR(100)
├── occupation: VARCHAR(100)
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP
    └── questionnaire_profiles (1:1)
        ├── id: SERIAL (PK)
        ├── user_id: UUID (FK → user_profiles.id, UNIQUE)
        ├── completion_percentage: INTEGER
        ├── last_answered_at: TIMESTAMP
        ├── created_at: TIMESTAMP
        └── updated_at: TIMESTAMP

questionnaire_categories (REFERENCE DATA)
├── id: INTEGER (PK)
├── name_ar: TEXT
├── name_en: TEXT
└── sort_order: INTEGER
    └── questionnaire_questions (1:N)
        ├── id: INTEGER (PK)
        ├── category_id: INTEGER (FK → questionnaire_categories.id)
        ├── question_ar: TEXT
        ├── question_en: TEXT
        ├── question_type: VARCHAR(30)
        ├── options_ar: JSONB
        ├── options_en: JSONB
        ├── weight: FLOAT
        ├── sort_order: INTEGER
        └── is_active: BOOLEAN
            └── user_questionnaire_answers (1:N)
                ├── id: INTEGER (PK)
                ├── user_profile_id: UUID (FK → user_profiles.id, NOT NULL)
                ├── question_id: INTEGER (FK → questionnaire_questions.id, NOT NULL)
                ├── answer_value: TEXT
                ├── answer_scale: INTEGER
                └── answered_at: TIMESTAMP

user_profiles (ROOT ENTITY)
    └── user_search_preferences (1:1)
        ├── id: INTEGER (PK)
        ├── user_profile_id: UUID (FK → user_profiles.id, NOT NULL, UNIQUE)
        ├── min_budget: INTEGER
        ├── max_budget: INTEGER
        ├── preferred_city: TEXT
        ├── preferred_government: TEXT
        ├── preferred_property_type: VARCHAR(20)
        ├── furnished: BOOLEAN
        ├── wifi: BOOLEAN
        ├── air_conditioning: BOOLEAN
        ├── balcony: BOOLEAN
        ├── private_bathroom: BOOLEAN
        ├── tenant_type: VARCHAR(20)
        ├── gender_preference: VARCHAR(20)
        ├── shared_room: BOOLEAN
        ├── created_at: TIMESTAMP
        └── updated_at: TIMESTAMP
```

## Verification Results

### Column Verification
- ✅ `user_questionnaire_answers` no longer has `user_id` column
- ✅ `user_questionnaire_answers` has `user_profile_id` (NOT NULL)
- ✅ `user_search_preferences` no longer has `user_id` column
- ✅ `user_search_preferences` has `user_profile_id` (NOT NULL, UNIQUE)

### Foreign Key Verification
- ✅ `user_questionnaire_answers.user_profile_id` → `user_profiles.id`
- ✅ `user_search_preferences.user_profile_id` → `user_profiles.id`
- ✅ `questionnaire_profiles.user_id` → `user_profiles.id`
- ✅ `questionnaire_questions.category_id` → `questionnaire_categories.id`

### API Verification
- ✅ Questionnaire repository methods work with `user_profile_id`
- ✅ Questionnaire API endpoints accept `user_profile_id`
- ✅ Admin endpoints updated to use `user_profile_id`
- ✅ Matching engine converts external user IDs to `user_profile_id` internally

### Code Search Results
- ✅ No remaining references to `user_questionnaire_answers.user_id` in application code
- ✅ No remaining references to `user_search_preferences.user_id` in application code
- ✅ Only references to removed columns are in migration files (expected)

## Breaking Changes

### API Changes
All questionnaire endpoints now require `user_profile_id` instead of external `user_id`:
- Frontend must use `user_profile_id` (UUID) instead of external user IDs
- Admin endpoints updated to return both `user_profile_id` and `external_user_id` for lookup

### Matching Engine
- Matching engine maintains compatibility with external .NET user IDs
- Internal conversion from external user ID to `user_profile_id` happens automatically
- No changes required for matching API consumers

## Migration Path

Since there is no production data and no backward compatibility requirement:
- ✅ All development data was truncated before schema changes
- ✅ No data migration was needed
- ✅ Clean slate with new schema

## Summary

The schema has been successfully simplified with:
- **Single source of truth**: `user_profiles.id` is now the only user reference in questionnaire tables
- **No duplication**: External user IDs only exist in `user_profiles.external_user_id`
- **Clean relationships**: All questionnaire tables properly reference `user_profiles.id` via foreign keys
- **Updated code**: All repositories, services, and API endpoints updated to use `user_profile_id`
- **Verified functionality**: Questionnaire APIs and matching engine tested and working correctly
