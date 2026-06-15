# Database Cleanup and Relationship Review Report

## Summary

Successfully performed database cleanup and relationship review to establish `user_profiles` as the root entity for all questionnaire-related data.

## Changes Made

### 1. New Table Created

**questionnaire_profiles**
- `id` (Integer, PK)
- `user_id` (UUID, FK → user_profiles.id, UNIQUE)
- `completion_percentage` (Integer, default 0)
- `last_answered_at` (DateTime)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- Index: `idx_questionnaire_profiles_user`

### 2. Foreign Keys Added

**user_questionnaire_answers**
- Added: `user_profile_id` (UUID, FK → user_profiles.id, nullable)
- Kept: `user_id` (String, for backward compatibility)
- Added Index: `idx_answers_user_profile`
- Existing FK: `question_id` → questionnaire_questions.id

**user_search_preferences**
- Added: `user_profile_id` (UUID, FK → user_profiles.id, nullable)
- Kept: `user_id` (String, for backward compatibility)
- Existing: No FKs previously

### 3. Data Cleanup

Truncated development data using `TRUNCATE ... RESTART IDENTITY CASCADE`:
- user_profiles (0 rows)
- questionnaire_profiles (0 rows)
- user_questionnaire_answers (0 rows)
- user_search_preferences (0 rows)

### 4. Tables Untouched (as required)

- questionnaire_categories
- questionnaire_questions
- scoring_weights

## ERD-Style Relationship Summary

```
user_profiles (ROOT ENTITY)
├── id (UUID, PK)
├── auth_user_id (UUID)
├── external_user_id (String, UNIQUE)
└── [other profile fields]

questionnaire_profiles
├── id (Integer, PK)
├── user_id (UUID, FK → user_profiles.id, UNIQUE) ← NEW FK
└── [completion tracking fields]

questionnaire_categories (UNTOUCHED)
├── id (Integer, PK)
└── [category fields]
    └── questionnaire_questions (UNTOUCHED)
        ├── id (Integer, PK)
        ├── category_id (Integer, FK → questionnaire_categories.id)
        └── [question fields]
            └── user_questionnaire_answers
                ├── id (Integer, PK)
                ├── user_id (String, kept for compatibility)
                ├── user_profile_id (UUID, FK → user_profiles.id) ← NEW FK
                ├── question_id (Integer, FK → questionnaire_questions.id)
                └── [answer fields]

user_search_preferences
├── id (Integer, PK)
├── user_id (String, kept for compatibility)
├── user_profile_id (UUID, FK → user_profiles.id) ← NEW FK
└── [preference fields]
```

## Final Table Structure

### user_profiles
```python
- id: UUID (PK)
- auth_user_id: UUID
- external_user_id: String (UNIQUE)
- full_name: Text
- phone: String(50)
- gender: String(20)
- birth_year: Integer
- nationality: String(100)
- occupation: String(100)
- created_at: DateTime
- updated_at: DateTime
Indexes: idx_user_profiles_auth, idx_user_profiles_external
Relationship: questionnaire_profile (1:1)
```

### questionnaire_profiles (NEW)
```python
- id: Integer (PK)
- user_id: UUID (FK → user_profiles.id, UNIQUE)
- completion_percentage: Integer (default 0)
- last_answered_at: DateTime
- created_at: DateTime
- updated_at: DateTime
Indexes: idx_questionnaire_profiles_user
Relationship: user (1:1)
```

### user_questionnaire_answers
```python
- id: Integer (PK)
- user_id: String (kept for compatibility)
- user_profile_id: UUID (FK → user_profiles.id, nullable) ← NEW
- question_id: Integer (FK → questionnaire_questions.id)
- answer_value: Text
- answer_scale: Integer
- answered_at: DateTime
Indexes: idx_answers_user, idx_answers_user_profile, idx_answers_question
UniqueConstraint: (user_id, question_id)
Relationship: question (N:1)
```

### user_search_preferences
```python
- id: Integer (PK)
- user_id: String (UNIQUE, kept for compatibility)
- user_profile_id: UUID (FK → user_profiles.id, nullable) ← NEW
- min_budget: Integer
- max_budget: Integer
- preferred_city: Text
- preferred_government: Text
- preferred_property_type: String(20)
- furnished: Boolean
- wifi: Boolean
- air_conditioning: Boolean
- balcony: Boolean
- private_bathroom: Boolean
- tenant_type: String(20)
- gender_preference: String(20)
- shared_room: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### questionnaire_categories (UNTOUCHED)
```python
- id: Integer (PK)
- name_ar: Text
- name_en: Text
- sort_order: Integer
Relationship: questions (1:N)
```

### questionnaire_questions (UNTOUCHED)
```python
- id: Integer (PK)
- category_id: Integer (FK → questionnaire_categories.id)
- question_ar: Text
- question_en: Text
- question_type: String(30)
- options_ar: JSONB
- options_en: JSONB
- weight: Float
- sort_order: Integer
- is_active: Boolean
Relationships: category (N:1), answers (1:N)
```

## Migration Files Created

1. **010_create_questionnaire_profiles_table.py** - Creates questionnaire_profiles table with FK to user_profiles
2. **011_add_user_profile_fk_to_answers.py** - Adds user_profile_id FK to user_questionnaire_answers
3. **012_add_user_profile_fk_to_search_preferences.py** - Adds user_profile_id FK to user_search_preferences
4. **013_truncate_development_data.py** - Truncates development data with CASCADE

## Verification Results

### Row Counts After Cleanup
- user_profiles: 0
- questionnaire_profiles: 0
- user_questionnaire_answers: 0
- user_search_preferences: 0

### Foreign Keys Verified
- questionnaire_profiles.user_id → user_profiles.id ✓
- user_questionnaire_answers.user_profile_id → user_profiles.id ✓
- user_questionnaire_answers.question_id → questionnaire_questions.id ✓
- user_search_preferences.user_profile_id → user_profiles.id ✓

## Relationship Verification

All questionnaire-related entities are now connected through user_profiles:
- questionnaire_profiles → user_profiles (direct FK)
- user_questionnaire_answers → user_profiles (via user_profile_id FK)
- user_search_preferences → user_profiles (via user_profile_id FK)
- questionnaire_questions → questionnaire_categories (unchanged)
- questionnaire_categories (standalone reference data, unchanged)

## Next Steps

Need to verify questionnaire APIs still work with the new schema.
