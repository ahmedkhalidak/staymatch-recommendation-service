# Matching System Production Notes

## Overview

The questionnaire and matching system uses dynamic weights loaded from the database, allowing automatic adaptation when questions are added, disabled, or weight values are modified without requiring code changes.

## Architecture

### Repository Structure

**`app/repositories/questionnaire_repo.py`**
- Dedicated repository for all questionnaire-related operations
- Methods:
  - `get_categories()` - Get all questionnaire categories with questions
  - `get_questions(category_id)` - Get active questions, optionally filtered by category
  - `save_answers(user_id, answers)` - Save or update questionnaire answers
  - `get_answers(user_id)` - Get all answers for a user
  - `get_active_question_weights()` - Load weights for all active questions
  - `get_active_question_metadata()` - Load full metadata for all active questions
  - `get_question_by_matching_key(matching_key)` - Get a question by its matching_key

**`app/services/matching/feature_encoding.py`**
- Core similarity calculation logic
- Functions:
  - `weighted_similarity()` - Calculate weighted similarity between two users' answers
  - `sim()` - Calculate similarity for a specific question
  - `load_questionnaire_weights_and_metadata()` - Load weights/metadata with caching
  - `clear_questionnaire_cache()` - Clear the cache (for testing or manual DB updates)
  - `_is_ordered_question()` - Determine if question has ordered vs categorical options
  - `_get_max_value()` - Get max value for ordered question (0-indexed)

**`app/services/matching/compatibility_engine.py`**
- Roommate matching engine
- Class: `CompatibilityEngine`
- Methods:
  - `compute_for_user(seeker_id)` - Compute roommate matches for a user
  - `_compute_pairwise()` - Calculate pairwise compatibility score
  - `_profile_only_score()` - Calculate score based only on profile data
  - `_aggregate_room_score()` - Aggregate pairwise scores into room score
  - `_check_tenant_eligibility()` - Check if seeker is eligible for a room
  - `_find_question_by_matching_key()` - Find question ID by matching_key

## matching_key Usage

### Purpose
The `matching_key` column in `questionnaire_questions` provides reliable question identification that doesn't depend on question IDs or text content.

### Standard matching_keys

| matching_key | Purpose | Notes |
|-------------|---------|-------|
| `age` | Age question | Excluded from questionnaire scoring (handled via profile.birth_year) |
| `occupation` | Occupation/status question | Excluded from questionnaire scoring (handled via profile.occupation) |
| `smoking` | Smoking preference | Special similarity calculation with penalty for mismatches |
| `sleep` | Sleep schedule | Ordered question |
| `cleanliness` | Cleanliness preferences | Ordered question |
| `social` | Social habits | Ordered question |
| `flexibility` | Flexibility with guests/rules | Ordered question |

### Setting matching_keys

When adding new questions to the database:

```sql
UPDATE questionnaire_questions 
SET matching_key = 'your_key_here' 
WHERE id = <question_id>;
```

### Finding Questions by matching_key

```python
from app.repositories.questionnaire_repo import QuestionnaireRepository

repo = QuestionnaireRepository()
question = repo.get_question_by_matching_key("smoking")
if question:
    print(f"Found smoking question: ID {question.id}")
```

## Dynamic Weights

### Loading Weights

Weights are loaded from `questionnaire_questions.weight` column for all questions where `is_active = true`.

```python
from app.services.matching.feature_encoding import load_questionnaire_weights_and_metadata

weights, metadata, smoking_question_id = load_questionnaire_weights_and_metadata()
# weights: {question_id: weight_value}
# metadata: {question_id: {question_type, options, weight, question_en, question_ar, matching_key}}
# smoking_question_id: ID of smoking question (or None)
```

### Weight Updates

To update question weights:

```sql
UPDATE questionnaire_questions 
SET weight = 0.15 
WHERE id = <question_id>;
```

The system will automatically use the new weight on the next cache refresh (10-minute TTL).

## Questionnaire Cache

### Cache Implementation

A simple TTL cache is implemented in `feature_encoding.py`:
- **TTL**: 10 minutes (600 seconds)
- **Cached data**: weights, metadata, smoking_question_id
- **Cache key**: `"weights_metadata"`

### Cache Behavior

- On first load: Data fetched from database and cached
- Subsequent loads: Data served from cache if not expired
- After expiration: Cache automatically refreshes on next load
- Manual clear: Call `clear_questionnaire_cache()` to force refresh

### Clearing Cache

```python
from app.services.matching.feature_encoding import clear_questionnaire_cache

# Clear cache (useful after manual DB updates or in tests)
clear_questionnaire_cache()
```

## Final Scoring Formula

### Pairwise Compatibility Score

```python
score = 0.85 * q_score + 0.08 * occupation_sim + 0.07 * age_sim
```

Where:
- `q_score`: Weighted questionnaire similarity (0-1)
- `occupation_sim`: Occupation similarity (1.0 if same, 0.5 if different)
- `age_sim`: Age similarity based on birth year difference (0-1)

### Questionnaire Similarity

```python
q_score = (sum(weight_i * similarity_i) / sum(weight_i)) * smoke_penalty
```

Where:
- `weight_i`: Weight of question i from database
- `similarity_i`: Similarity score for question i (0-1)
- `smoke_penalty`: 0.3 if smoking mismatch, otherwise 1.0

### Ordered Question Similarity

For ordered questions (e.g., sleep schedule, cleanliness):

```python
similarity = 1.0 - abs(answer_a - answer_b) / max_val
```

Where `max_val = len(options) - 1` (0-indexed max value).

**Example** with 4 options [0, 1, 2, 3]:
- Difference 0: 1.0 - 0/3 = 1.0
- Difference 1: 1.0 - 1/3 = 0.666
- Difference 3: 1.0 - 3/3 = 0.0

### Smoking Question Similarity

Special handling for smoking question:
- Difference ≤ 1: similarity = 1.0
- Difference = 2: similarity = 0.1
- Difference = 3: similarity = 0.0
- If similarity < 0.5: applies 0.3 penalty to overall questionnaire score

### Categorical Question Similarity

For categorical questions (exact match required):
- Same answer: similarity = 1.0
- Different answer: similarity = 0.0

## Age & Occupation Handling

### Exclusion from Questionnaire Scoring

Age and occupation questions are **excluded** from questionnaire scoring to prevent duplicate counting:
- Age is computed from `profile.birth_year` field
- Occupation is computed from `profile.occupation` field

This is implemented in `CompatibilityEngine._compute_pairwise()`:

```python
# Exclude age and occupation questions from questionnaire scoring
filtered_answers_a = {k: v for k, v in answers_a.items() 
                      if int(k) not in [self.age_question_id, self.occupation_question_id]}
filtered_answers_b = {k: v for k, v in answers_b.items() 
                      if int(k) not in [self.age_question_id, self.occupation_question_id]}
filtered_weights = {k: v for k, v in self.weights.items() 
                     if k not in [self.age_question_id, self.occupation_question_id]}
```

### Identification via matching_key

Age and occupation questions are identified by their `matching_key`:
- Age: `matching_key = 'age'`
- Occupation: `matching_key = 'occupation'`

This ensures correct identification even if question IDs change.

## Gender Handling

### Hard Filter Only

Gender is **NOT** used in scoring. It is only used as a hard filter in `_check_tenant_eligibility()` to determine if a seeker is eligible for a room based on the room's allowed_tenants configuration.

### Eligibility Check

The `_check_tenant_eligibility()` method checks:
- Student gender restrictions
- Worker gender restrictions
- Occupation type restrictions (students only, workers only, etc.)

Gender does not affect the compatibility score in any way.

## Adding New Questions Safely

### Step 1: Add Question to Database

```sql
INSERT INTO questionnaire_questions (
    category_id,
    question_ar,
    question_en,
    question_type,
    options_ar,
    options_en,
    weight,
    sort_order,
    is_active,
    matching_key
) VALUES (
    <category_id>,
    'سؤال بالعربية',
    'Question in English',
    'ordered',  -- or 'categorical'
    ['option1_ar', 'option2_ar', 'option3_ar'],
    ['option1_en', 'option2_en', 'option3_en'],
    0.10,  -- weight (sum should ideally be ~1.0 across all questions)
    10,    -- sort_order
    true,  -- is_active
    'your_matching_key'  -- optional but recommended
);
```

### Step 2: Set matching_key (if not set during insert)

```sql
UPDATE questionnaire_questions 
SET matching_key = 'your_key_here' 
WHERE id = <new_question_id>;
```

### Step 3: Run Migration (if needed)

If this is a new deployment, run migrations:

```bash
alembic upgrade head
```

### Step 4: Clear Cache (if already running)

```python
from app.services.matching.feature_encoding import clear_questionnaire_cache
clear_questionnaire_cache()
```

Or restart the service (cache is in-memory).

### Step 5: Verify

The new question will automatically be included in matching calculations on the next:
- Service restart, or
- Cache expiration (10 minutes), or
- Manual cache clear

## Database Schema

### questionnaire_questions Table

```sql
CREATE TABLE questionnaire_questions (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES questionnaire_categories(id),
    question_ar TEXT NOT NULL,
    question_en TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL,  -- 'ordered', 'categorical', etc.
    options_ar JSONB,
    options_en JSONB,
    weight DOUBLE PRECISION DEFAULT 1.0,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    matching_key VARCHAR(50)  -- NEW: for reliable question identification
);
```

### Indexes

```sql
CREATE INDEX idx_questionnaire_matching_key ON questionnaire_questions(matching_key);
```

## Migration

### Adding matching_key Column

Migration file: `alembic/versions/009_add_matching_key.py`

```bash
# Apply migration
alembic upgrade head

# Rollback (if needed)
alembic downgrade -1
```

## Testing

### Unit Tests

Run matching tests:

```bash
PYTHONPATH=. python -m pytest tests/test_matching.py -v
```

### Clearing Cache in Tests

```python
from app.services.matching.feature_encoding import clear_questionnaire_cache

# Clear cache before each test
clear_questionnaire_cache()
```

## Troubleshooting

### Question Not Appearing in Matching

1. Check `is_active = true` in database
2. Check `weight > 0` in database
3. Clear cache: `clear_questionnaire_cache()`
4. Check logs for errors

### Wrong Question Identified by matching_key

1. Verify `matching_key` is set correctly in database
2. Check for duplicate `matching_key` values (should be unique)
3. Clear cache after updating

### Cache Not Refreshing

1. Wait 10 minutes for automatic expiration
2. Or manually clear: `clear_questionnaire_cache()`
3. Or restart the service

### Age/Occupation Still Counted Twice

1. Verify `matching_key = 'age'` and `matching_key = 'occupation'` are set
2. Check `_compute_pairwise()` is filtering correctly
3. Clear cache after updating matching_keys

## Performance Considerations

### Cache Benefits

- Reduces database queries by ~90% for matching operations
- 10-minute TTL balances freshness with performance
- Cache is in-memory (per process)

### Scaling

For high-traffic deployments:
- Consider using Redis for distributed caching
- Increase TTL if questions change infrequently
- Monitor cache hit rate

## Security Notes

### matching_key Values

- Should be lowercase alphanumeric with underscores
- Avoid using sensitive information in matching_key
- matching_key is not user-facing (internal use only)

### Weight Values

- Weights are loaded from database - ensure proper access controls
- Weight changes affect all users immediately after cache refresh
- Consider weight change audit logging for production

## Future Improvements

1. **Distributed Caching**: Use Redis for multi-instance deployments
2. **Weight Change Events**: Emit events on weight changes to trigger cache refresh
3. **matching_key Validation**: Add database constraint for valid matching_key values
4. **Question Type Validation**: Ensure question_type matches actual options
5. **Weight Sum Validation**: Warn if weights don't sum to ~1.0
6. **Cache Metrics**: Add monitoring for cache hit/miss rates
