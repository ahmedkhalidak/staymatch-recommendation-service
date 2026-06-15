# Source of Truth Rules

## Overview

This document defines the single source of truth for each data field to avoid duplication and maintain data consistency across the system.

## User Profile Data

### Birth Year vs Age Group

**Source of Truth: `user_profiles.birth_year`**

- **Primary Storage:** `user_profiles.birth_year` (INTEGER)
  - Stores the actual birth year (e.g., 2004)
  - Used for precise age calculations
  - Source of truth for all age-related operations

- **Derived Data:** `questionnaire_answers.age_group` (from questionnaire)
  - Stores categorical age group (e.g., "22-25", "26-30")
  - Used for questionnaire-based matching
  - Derived from birth_year for compatibility with questionnaire logic
  - **NOT** the source of truth - calculated from birth_year

**Usage:**
```python
# Get actual age from birth_year
current_year = datetime.now().year
age = current_year - user.birth_year

# Get age group for questionnaire matching
age_group = questionnaire_repo.get_age_group(user.external_user_id)
```

**Rationale:**
- Birth year is precise and immutable
- Age group is a derived categorization for matching algorithms
- Storing both allows flexibility in matching logic while maintaining data integrity

### Occupation Data

**Source of Truth: `user_profiles.occupation`**

- **Primary Storage:** `user_profiles.occupation` (VARCHAR)
  - Stores actual occupation/job title (e.g., "Software Engineer", "Student")
  - Free-form text field
  - Source of truth for all occupation-related operations

- **Derived Data:** `questionnaire_answers.occupation_status` (from questionnaire)
  - Stores categorical occupation status (e.g., "student", "worker", "unemployed")
  - Used for questionnaire-based matching
  - Derived from occupation for compatibility with questionnaire logic
  - **NOT** the source of truth - categorized from occupation

**Usage:**
```python
# Get actual occupation
occupation = user.occupation

# Get occupation status for questionnaire matching
occupation_status = questionnaire_repo.get_occupation_status(user.external_user_id)
```

**Rationale:**
- Occupation is detailed and flexible
- Occupation status is a simplified categorization for matching algorithms
- Storing both allows detailed profiling while enabling categorical matching

## Questionnaire Data

### Completion Status

**Source of Truth: `user_questionnaire_answers` table**

- **Primary Storage:** Individual answer records in `user_questionnaire_answers`
  - Each answer is stored as a separate row
  - Source of truth for completion calculations

- **Derived Data:** Completion percentage, answered count, completed status
  - Calculated at runtime from `user_questionnaire_answers`
  - **NOT** stored in any cache table
  - Computed on-demand when needed

**Usage:**
```python
# Calculate completion at runtime
total_questions = session.query(QuestionnaireQuestion).filter(is_active=True).count()
answered_count = session.query(UserQuestionnaireAnswer).filter(
    user_profile_id=user_profile_id
).count()
completion_percentage = (answered_count / total_questions * 100) if total_questions > 0 else 0
```

**Rationale:**
- Avoids data duplication
- Always reflects current state
- Simplifies data maintenance
- No cache table needed (removed `questionnaire_profiles` table)

## Data Flow Summary

### External User Data Flow
```
.NET API → user_profiles.external_user_id (source of truth)
         ↓
    user_profiles.id (internal PK)
         ↓
    All questionnaire tables via user_profile_id FK
```

### Age Data Flow
```
user_profiles.birth_year (source of truth)
         ↓
    Calculate actual age
         ↓
    Derive age_group for matching (if needed)
```

### Occupation Data Flow
```
user_profiles.occupation (source of truth)
         ↓
    Categorize for matching
         ↓
    occupation_status in questionnaire answers (if needed)
```

### Questionnaire Completion Flow
```
user_questionnaire_answers (source of truth)
         ↓
    Count answers at runtime
         ↓
    Calculate completion percentage
         ↓
    No cache table needed
```

## Rules Summary

1. **Single Source of Truth:** Each data element has one primary storage location
2. **Derived Data:** Categorical or calculated data can be derived from source of truth
3. **No Duplication:** Avoid storing the same data in multiple places
4. **Runtime Calculation:** Calculate metrics (completion percentage) at runtime from source data
5. **Flexible Matching:** Store both detailed and categorical data when needed for different use cases

## Benefits

- **Data Consistency:** Single source of truth eliminates synchronization issues
- **Simplified Maintenance:** No need to update multiple locations
- **Accurate Reporting:** Always reflects current state
- **Flexible Architecture:** Easy to add new derived metrics without schema changes
- **Clean Schema:** Removed unused cache table (`questionnaire_profiles`)
