# Runtime-Verified System Documentation

**Generated:** June 13, 2026  
**Method:** Actual code execution with real database  
**Environment:** Production-like database state

---

## CRITICAL FINDING

**The database schema in the actual database DOES NOT MATCH the code expectations.**

The code references tables that do not exist in the database. This is a **runtime blocking issue** for property/room recommendations and matching with property occupants.

---

## 1. Actual Database State

### Tables That EXIST (14 tables)

```
✓ alembic_version: 1 row
✓ conversations: 1 row
✓ messages: 0 rows
✓ questionnaire_categories: 4 rows
✓ questionnaire_profiles_view: 0 rows
✓ questionnaire_questions: 13 rows
✓ scoring_weights: 20 rows
✓ search_history: 0 rows
✓ session_analytics: 32 rows
✓ user_feedback_weights: 0 rows
✓ user_interactions: 0 rows
✓ user_profiles: 1 row
✓ user_questionnaire_answers: 52 rows
✓ user_search_preferences: 0 rows
```

### Tables That DO NOT EXIST (6 tables - Referenced in Code)

```
✗ synced_properties: MISSING
✗ synced_rooms: MISSING
✗ synced_amenities: MISSING
✗ synced_allowed_tenants: MISSING
✗ property_recommendations: MISSING
✗ room_recommendations: MISSING
```

### Impact

- **Property recommendations:** CANNOT FUNCTION (no synced_properties table)
- **Room recommendations:** CANNOT FUNCTION (no synced_rooms table)
- **Matching with property occupants:** CANNOT FUNCTION (no property data)
- **Questionnaire system:** FUNCTIONS (tables exist)
- **Matching engine (questionnaire-only):** FUNCTIONS (uses questionnaire data only)

---

## 2. Questionnaire System - Runtime Verified

### Categories (Actual: 4 categories)

```
ID 1: Personal Background (sort: 1)
ID 2: Daily Schedule (sort: 2)
ID 3: Lifestyle (sort: 3)
ID 4: Social Compatibility (sort: 4)
```

### Questions (Actual: 13 active questions, NOT 16)

**Category 1 - Personal Background:**
- ID 1: "What is your age group?" - Type: ordered, Weight: 3.0, Options: ['18-21', '22-25', '26-30', '30+'], Matching Key: NOT SET
- ID 2: "Which option best describes you?" - Type: categorical, Weight: 5.0, Options: ['Student', 'Employee', 'Freelancer', 'Student and Employee'], Matching Key: NOT SET
- ID 3: "What is your field of study or work?" - Type: categorical, Weight: 5.0, Options: ['Technology', 'Engineering', 'Medical', 'Business', 'Other'], Matching Key: NOT SET

**Category 2 - Daily Schedule:**
- ID 4: "When are you usually busiest during the day?" - Type: ordered, Weight: 10.0, Options: ['Morning', 'Noon', 'Afternoon', 'Evening', 'Night'], Matching Key: NOT SET
- ID 5: "When do you usually go to sleep?" - Type: ordered, Weight: 14.0, Options: ['Before 10 PM', '10 PM - 12 AM', '12 AM - 2 AM', 'After 2 AM'], Matching Key: NOT SET
- ID 6: "What is the first thing you do when you get home?" - Type: categorical, Weight: 4.0, Options: ['Rest', 'Study or Work', 'Eat', 'Socialize'], Matching Key: NOT SET

**Category 3 - Lifestyle:**
- ID 7: "How do you react to mess in shared spaces?" - Type: ordered, Weight: 14.0, Options: ['Cannot tolerate it', 'It bothers me', 'Sometimes acceptable', 'Does not bother me'], Matching Key: NOT SET
- ID 8: "How do you usually spend your free days?" - Type: categorical, Weight: 3.0, Options: ['At home', 'With friends', 'Going out often', 'Depends'], Matching Key: NOT SET
- ID 9: "How much do you enjoy group activities?" - Type: ordered, Weight: 7.0, Options: ['Love them', 'Sometimes', 'Rarely', 'Prefer being alone'], Matching Key: NOT SET
- ID 10: "Which environment do you prefer for studying or working?" - Type: ordered, Weight: 8.0, Options: ['Complete silence', 'Mostly quiet', 'Some noise', 'No preference'], Matching Key: NOT SET

**Category 4 - Social Compatibility:**
- ID 11: "What is your attitude toward smoking?" - Type: smoking, Weight: 14.0, Options: ['I do not smoke and prefer non-smokers', 'I do not smoke but do not mind', 'I smoke but do not mind', 'I smoke and prefer smokers'], Matching Key: NOT SET
- ID 12: "What annoys you most in shared living?" - Type: categorical, Weight: 5.0, Options: ['Noise', 'Messiness', 'Smoking', 'Lack of privacy'], Matching Key: NOT SET
- ID 13: "How flexible are you when living with different personalities?" - Type: ordered, Weight: 8.0, Options: ['Very flexible', 'Flexible', 'Somewhat flexible', 'Not flexible'], Matching Key: NOT SET

### Answers (Actual: 52 total answers from 4 users)

**Top users by answer count:**
- 3ee32cef-cdbe-4a63-94a1-819e34a88fec: 13 answers (100% complete)
- f51e64a7-8138-488a-9f69-8ab32226bfef: 13 answers (100% complete)
- 0b366cc1-77da-4a97-9587-daf5341dc519: 13 answers (100% complete)
- 1121c342-dd7a-4a29-bc66-c94f6aa43212: 13 answers (100% complete)

**Sample answers (User: 3ee32cef-cdbe-4a63-94a1-819e34a88fec):**
```
Question 1: answer_scale=1, answer_value=2 (Age group: 22-25)
Question 2: answer_scale=0, answer_value=1 (Occupation: Student)
Question 3: answer_scale=0, answer_value=1 (Field: Technology)
Question 4: answer_scale=4, answer_value=5 (Busiest: Night)
Question 5: answer_scale=2, answer_value=3 (Sleep: 12 AM - 2 AM)
Question 6: answer_scale=1, answer_value=2 (First activity: Study or Work)
Question 7: answer_scale=0, answer_value=1 (Mess: Cannot tolerate)
Question 8: answer_scale=1, answer_value=2 (Free days: With friends)
Question 9: answer_scale=1, answer_value=2 (Group activities: Sometimes)
Question 10: answer_scale=0, answer_value=1 (Study environment: Complete silence)
Question 11: answer_scale=0, answer_value=1 (Smoking: Non-smoker, prefer non-smokers)
Question 12: answer_scale=1, answer_value=2 (Biggest issue: Messiness)
Question 13: answer_scale=1, answer_value=2 (Flexibility: Flexible)
```

**Answer storage format:**
- Database stores: `answer_scale` (0-based integer), `answer_value` (string)
- API returns: machine_key → answer_scale (1-based integer)
- Conversion: API 1-based → Database 0-based (subtract 1)

---

## 3. API Endpoints - Runtime Verified

### Working Endpoints

#### GET `/health`
- **Status:** ✓ WORKS
- **Response:** `{"status": "healthy", "database": "connected"}`
- **Service called:** None
- **Repository called:** None

#### GET `/questionnaire/questions`
- **Status:** ✓ WORKS
- **Response:** Array of categories with questions and options
- **Service called:** `QuestionnaireService.get_all_questions()`
- **Repository called:** `QuestionnaireRepository.get_categories()`
- **External APIs:** None
- **Actual response structure:**
```json
[
  {
    "category": {"id": 1, "name_ar": "الخلفية الشخصية", "name_en": "Personal Background"},
    "questions": [
      {
        "id": 1,
        "key": "age_group",
        "question_ar": "ما هي فئتك العمرية؟",
        "question_en": "What is your age group?",
        "question_type": "ordered",
        "weight": 3.0,
        "options": {
          "1": {"ar": "18-21", "en": "18-21"},
          "2": {"ar": "22-25", "en": "22-25"},
          "3": {"ar": "26-30", "en": "26-30"},
          "4": {"ar": "30+", "en": "30+"}
        }
      }
    ]
  }
]
```

#### GET `/questionnaire/status/{user_id}`
- **Status:** ✓ WORKS
- **Tested with:** `3ee32cef-cdbe-4a63-94a1-819e34a88fec`
- **Response:**
```json
{
  "user_id": "3ee32cef-cdbe-4a63-94a1-819e34a88fec",
  "answered_questions": 13,
  "total_questions": 13,
  "completed": true,
  "completion_percentage": 100.0,
  "completed_at": "2026-06-12T17:11:11.302792"
}
```
- **Service called:** None (direct DB query in router)
- **Repository called:** `QuestionnaireRepository.get_questionnaire_status()`

#### GET `/admin/questionnaire/answers/{user_id}`
- **Status:** ✓ WORKS
- **Tested with:** `3ee32cef-cdbe-4a63-94a1-819e34a88fec`
- **Response:**
```json
{
  "user_id": "3ee32cef-cdbe-4a63-94a1-819e34a88fec",
  "answers": {
    "age_group": 2,
    "occupation_status": 1,
    "study_or_work_field": 1,
    "busiest_time": 5,
    "sleep_time": 3,
    "first_activity_home": 2,
    "mess_tolerance": 1,
    "free_day_style": 2,
    "group_activity_preference": 2,
    "study_environment": 1,
    "smoking_preference": 1,
    "biggest_shared_living_issue": 2,
    "flexibility_level": 2
  }
}
```
- **Service called:** `QuestionnaireService.transform_answers_to_map()`
- **Repository called:** `QuestionnaireRepository.get_answers()`

### Endpoints That CANNOT Be Tested

#### GET `/match/property/{user_id}/{property_id}`
- **Status:** ✗ CANNOT TEST
- **Reason:** Requires property data from synced_properties table (MISSING)
- **Would call:** `CompatibilityEngine.compute_property_and_room_scores()`
- **Would call external API:** `.NET Property API` (not tested due to missing property data)

#### POST `/match/shared-properties/{user_id}`
- **Status:** ✗ CANNOT TEST
- **Reason:** Requires property data from synced_properties table (MISSING)
- **Would call:** `CompatibilityEngine.compute_properties_match_scores()`

#### POST `/questionnaire/answers/{user_id}`
- **Status:** ✗ NOT TESTED
- **Reason:** Would modify data, not tested in verification
- **Would call:** `QuestionnaireService.validate_answers_against_options()`, `transform_answers_from_map()`

#### Admin endpoints (POST, DELETE)
- **Status:** ✗ NOT TESTED
- **Reason:** Would modify data, not tested in verification

---

## 4. Matching Engine - Runtime Verified

### Initialization

**Actual runtime values:**
```
✓ CompatibilityEngine initialized successfully
  Smoking question ID: None
  Age question ID: None
  Occupation question ID: None
```

**Critical finding:** All matching_key values are `None` in the database. The code attempts to find questions by matching_key but cannot find them because the column is not populated.

### Questionnaire Weights (Actual: 13 questions)

```
ID 1: weight=3.0
ID 2: weight=5.0
ID 3: weight=5.0
ID 4: weight=10.0
ID 5: weight=14.0
ID 6: weight=4.0
ID 7: weight=14.0
ID 8: weight=3.0
ID 9: weight=7.0
ID 10: weight=8.0
ID 11: weight=14.0
ID 12: weight=5.0
ID 13: weight=8.0
```

Total weight: 100.0

### Pairwise Similarity Calculation - Actual Execution

**Test users:**
- User A: `3ee32cef-cdbe-4a63-94a1-819e34a88fec`
- User B: `f51e64a7-8138-488a-9f69-8ab32226bfef`

**User A answers (0-based scales):**
```
{'1': 1, '2': 0, '3': 0, '4': 4, '5': 2, '6': 1, '7': 0, '8': 1, '9': 1, '10': 0, '11': 0, '12': 1, '13': 1}
```

**User B answers (0-based scales):**
```
{'1': 3, '2': 2, '3': 4, '4': 0, '5': 3, '6': 3, '7': 3, '8': 2, '9': 3, '10': 3, '11': 3, '12': 0, '13': 3}
```

**Individual question similarities (actual runtime values):**

| Question | Type | User A | User B | Similarity | Weight | Contribution |
|----------|------|--------|--------|------------|--------|--------------|
| 1 | ordered | 1 | 3 | 0.3333 | 3.0 | 1.0000 |
| 2 | categorical | 0 | 2 | 0.0000 | 5.0 | 0.0000 |
| 3 | categorical | 0 | 4 | 0.0000 | 5.0 | 0.0000 |
| 4 | ordered | 4 | 0 | 0.0000 | 10.0 | 0.0000 |
| 5 | ordered | 2 | 3 | 0.6667 | 14.0 | 9.3333 |
| 6 | categorical | 1 | 3 | 0.0000 | 4.0 | 0.0000 |
| 7 | ordered | 0 | 3 | 0.0000 | 14.0 | 0.0000 |
| 8 | categorical | 1 | 2 | 0.0000 | 3.0 | 0.0000 |
| 9 | ordered | 1 | 3 | 0.3333 | 7.0 | 2.3333 |
| 10 | ordered | 0 | 3 | 0.0000 | 8.0 | 0.0000 |
| 11 | smoking | 0 | 3 | 0.0000 | 14.0 | 0.0000 |
| 12 | categorical | 1 | 0 | 0.0000 | 5.0 | 0.0000 |
| 13 | ordered | 1 | 3 | 0.3333 | 8.0 | 2.6667 |

**Total weighted similarity:** 0.1533

**Formula executed:**
```
similarity = (Σ(weight_i * sim_i)) / Σ(weight_i) * smoke_penalty
similarity = (15.3333) / 100.0 * 1.0
similarity = 0.1533
```

### Pairwise Score Calculation - Actual Execution

**Formula executed:**
```
pairwise_score = 0.85 * questionnaire_sim + 0.08 * occupation_sim + 0.07 * age_sim
```

**Actual values:**
- Questionnaire similarity (filtered): 0.1533
- Occupation similarity: 1.0 (both profiles are None, defaults to 1.0)
- Age similarity: 1.0 (both profiles are None, defaults to 1.0)

**Calculation:**
```
pairwise_score = 0.85 * 0.1533 + 0.08 * 1.0 + 0.07 * 1.0
pairwise_score = 0.1303 + 0.08 + 0.07
pairwise_score = 0.2803
```

**Final pairwise score:** 0.2803

### Critical Finding: Profile Data

**User profiles in database:** 1 total
**Test users have profiles:** None

Both test users (3ee32cef-cdbe-4a63-94a1-819e34a88fec and f51e64a7-8138-488a-9f69-8ab32226bfef) do NOT have profiles in the user_profiles table. The matching engine defaults occupation and age similarity to 1.0 when profiles are missing.

---

## 5. Scoring Weights - Runtime Verified

### Actual Weights in Database (20 total)

**Property group (7 weights):**
```
budget: 0.3
location: 0.25
amenities: 0.15
tenant: 0.1
furnished: 0.05
property_type: 0.1
recency: 0.05
```

**Room group (8 weights):**
```
budget: 0.25
location: 0.2
capacity: 0.15
amenities: 0.1
tenant: 0.1
furnished: 0.05
room_type: 0.1
recency: 0.05
```

**Matching group (5 weights):**
```
questionnaire: 0.5
gender: 0.15
occupation: 0.1
age_group: 0.1
lifestyle: 0.15
```

**Note:** These weights differ from the hardcoded defaults in `utils/weights.py`. The database weights take precedence when loaded by the Ranker.

---

## 6. Properties 122, 123, 138 - Cannot Verify

**Status:** ✗ CANNOT VERIFY

**Reason:** The `synced_properties` table does not exist in the database. Without this table, there is no property data to:

- Fetch occupants
- Calculate property match scores
- Calculate room match scores
- Execute matching engine with property data

**What would be needed:**
1. Run migration 001 to create synced_properties table
2. Run data sync from MSSQL to populate the table
3. Then properties 122, 123, 138 could be verified

**Current state:** Properties do not exist in the database.

---

## 7. External APIs - Cannot Verify

**Status:** ✗ CANNOT VERIFY

**Reason:** External API calls require property data to test. Without synced_properties table, there are no property IDs to test with.

**External APIs that would be called (not tested):**
- GET /api/Property/GetAllWithRooms
- GET /api/Property/{propertyId}
- GET /api/Property/Room/occupants?id={roomId}
- GET /api/Property/Property/occupants?id={propertyId}
- GET /api/ViewUserProfile/{userId}

**Configuration:** PROPERTY_API_BASE_URL and PROPERTY_API_TOKEN are set in environment but not tested due to missing property data.

---

## 8. Services - Runtime Verified

### QuestionnaireService

**Status:** ✓ WORKS

**Methods tested:**
- `get_all_questions()` - Returns categories with questions
- `transform_answers_to_map()` - Converts question_id to machine_key
- `validate_answers_against_options()` - Validates answer ranges

**Machine key mapping (hardcoded in service):**
```python
{
    1: "age_group",
    2: "occupation_status",
    3: "study_or_work_field",
    4: "busiest_time",
    5: "sleep_time",
    6: "first_activity_home",
    7: "mess_tolerance",
    8: "free_day_style",
    9: "group_activity_preference",
    10: "study_environment",
    11: "smoking_preference",
    12: "biggest_shared_living_issue",
    13: "flexibility_level",
}
```

**Critical finding:** The service uses hardcoded mapping instead of reading from the database `matching_key` column (which is None for all questions).

### CompatibilityEngine

**Status:** ✓ PARTIALLY WORKS

**Methods tested:**
- `__init__()` - Initializes successfully
- `_compute_pairwise()` - Works with questionnaire data only
- `_profile_only_score()` - Works (defaults to 0.6 * occupation + 0.4 * age)

**Methods NOT tested (require property data):**
- `compute_for_user()` - Requires property data from .NET API
- `compute_property_and_room_scores()` - Requires property data
- `compute_properties_match_scores()` - Requires property data

**Critical findings:**
1. Smoking question ID is None (matching_key not set in DB)
2. Age question ID is None (matching_key not set in DB)
3. Occupation question ID is None (matching_key not set in DB)
4. The engine cannot identify special questions without matching_key

### PropertyRecommender

**Status:** ✗ CANNOT FUNCTION

**Reason:** Requires `synced_properties` table which does not exist.

**Methods NOT tested:**
- `recommend()` - Requires property data
- `_prefilter()` - Requires property data
- `_check_cache()` - Requires property_recommendations table (MISSING)

### RoomRecommender

**Status:** ✗ CANNOT FUNCTION

**Reason:** Requires `synced_rooms` table which does not exist.

**Methods NOT tested:**
- `recommend()` - Requires room data
- `_check_cache()` - Requires room_recommendations table (MISSING)

---

## 9. Repositories - Runtime Verified

### QuestionnaireRepository

**Status:** ✓ WORKS

**Methods tested:**
- `get_categories()` - Returns 4 categories
- `get_questions()` - Returns 13 active questions
- `get_answers()` - Returns user answers
- `get_questionnaire_status()` - Returns completion status
- `get_active_question_weights()` - Returns weights dict
- `get_active_question_metadata()` - Returns metadata dict

### PropertyRepository

**Status:** ✗ CANNOT FUNCTION

**Reason:** Requires `synced_properties`, `synced_rooms`, `synced_amenities`, `synced_allowed_tenants` tables which do not exist.

### UserRepository

**Status:** ✓ PARTIALLY WORKS

**Methods tested:**
- `get_profile()` - Returns 1 profile (external_user_id: 1121c342-dd7a-4a29-bc66-c94f6aa43212)

**Profile data:**
```
External ID: 1121c342-dd7a-4a29-bc66-c94f6aa43212
Name: Test User
Gender: male
Birth Year: 1995
Occupation: Engineer
```

### WeightRepository

**Status:** ✓ WORKS

**Methods tested:**
- `get_weights()` - Returns weights from database
- `get_all_weights()` - Returns all 20 weights

---

## 10. Current Production Behavior

### What Works (Current Production)

1. **Questionnaire API:**
   - GET /questionnaire/questions ✓
   - GET /questionnaire/status/{user_id} ✓
   - GET /admin/questionnaire/answers/{user_id} ✓

2. **Questionnaire Data:**
   - 4 categories exist
   - 13 active questions exist
   - 52 answers from 4 users exist
   - Machine key mapping works (hardcoded)

3. **Matching Engine (Questionnaire-Only):**
   - Weighted similarity calculation works
   - Pairwise score calculation works
   - Formula: 0.85 * questionnaire + 0.08 * occupation + 0.07 * age

4. **Database:**
   - PostgreSQL connection works
   - Questionnaire tables work
   - User profiles table works (1 profile)
   - Scoring weights table works (20 weights)

### What Does NOT Work (Current Production)

1. **Property Recommendations:**
   - synced_properties table MISSING
   - PropertyRecommender cannot function
   - No property data available

2. **Room Recommendations:**
   - synced_rooms table MISSING
   - RoomRecommender cannot function
   - No room data available

3. **Matching with Property Occupants:**
   - No property data to fetch occupants
   - Cannot compute property/room match scores
   - Cannot execute compute_for_user(), compute_property_and_room_scores(), compute_properties_match_scores()

4. **Recommendation Caching:**
   - property_recommendations table MISSING
   - room_recommendations table MISSING
   - No caching possible

5. **External API Integration:**
   - Cannot test .NET Property API calls
   - No property IDs to test with
   - PropertyAPIClient not tested

---

## 11. Historical vs Current vs Planned

### Historical Behavior (Based on Code)

The code was written to expect:
- 16 questions (actual: 13)
- matching_key populated in database (actual: all None)
- Property sync tables (actual: MISSING)
- Recommendation cache tables (actual: MISSING)
- External API integration for property data (actual: NOT TESTED)

### Current Behavior (Runtime Verified)

**Actually working:**
- 13 questions (not 16)
- No matching_key values (all None)
- Questionnaire-only matching (no property data)
- Hardcoded machine key mapping
- Database weights override hardcoded defaults

**Actually broken:**
- Property recommendations (no tables)
- Room recommendations (no tables)
- Property-based matching (no data)
- External API integration (not tested)

### Planned Behavior (Based on Code)

The code is designed to:
- Sync property data from MSSQL to PostgreSQL
- Use .NET Property API for live occupant data
- Cache recommendations for 24 hours
- Support A/B testing with database weights
- Support questionnaire-based property scoring

**Gap:** Database migrations have not created the required tables.

---

## 12. Exact Formulas Currently Executed

### Questionnaire Similarity Formula

**Actual formula executed:**
```python
similarity = (Σ(weight_i * sim_i)) / Σ(weight_i) * smoke_penalty
```

**Where:**
- `weight_i`: Question weight from database (3.0 to 14.0)
- `sim_i`: Individual question similarity (0.0 to 1.0)
- `smoke_penalty`: 1.0 normally, 0.3 if smoking mismatch

**Individual similarity calculation:**
```python
# For ordered questions:
sim = 1.0 - |answer_a - answer_b| / max_value
# max_value = len(options) - 1

# For categorical questions:
sim = 1.0 if answer_a == answer_b else 0.0

# For smoking question (special):
if difference <= 1: sim = 1.0
elif difference == 2: sim = 0.1
else: sim = 0.0
```

### Pairwise Score Formula

**Actual formula executed:**
```python
pairwise_score = 0.85 * questionnaire_sim + 0.08 * occupation_sim + 0.07 * age_sim
```

**Where:**
- `questionnaire_sim`: Weighted similarity (0.1533 in test)
- `occupation_sim`: 1.0 if match, 0.5 if mismatch, 1.0 if profiles missing
- `age_sim`: max(0.0, 1.0 - age_diff / 20.0), 1.0 if profiles missing

**Actual calculation (test case):**
```python
pairwise_score = 0.85 * 0.1533 + 0.08 * 1.0 + 0.07 * 1.0
pairwise_score = 0.1303 + 0.08 + 0.07
pairwise_score = 0.2803
```

### Room Aggregation Formula

**Formula (NOT TESTED - requires property data):**
```python
room_score = 0.6 * min_pairwise_score + 0.4 * avg_pairwise_score
room_score += min(0.1, empty_spots * 0.03)
room_score = min(1.0, room_score)
```

### Property Score Formula

**Formula (NOT TESTED - requires property data):**
```python
property_score = average of all pairwise scores in property
```

---

## 13. Summary

### Runtime Verification Results

**Verified and Working:**
- ✓ Database connection (PostgreSQL)
- ✓ Questionnaire system (4 categories, 13 questions, 52 answers)
- ✓ Questionnaire API endpoints (3 endpoints tested)
- ✓ Matching engine (questionnaire-only pairwise calculation)
- ✓ Scoring weights (20 weights in database)
- ✓ User profiles (1 profile exists)

**Verified and NOT Working:**
- ✗ Property recommendations (synced_properties table MISSING)
- ✗ Room recommendations (synced_rooms table MISSING)
- ✗ Matching with property occupants (no property data)
- ✗ Recommendation caching (cache tables MISSING)
- ✗ External API integration (not tested due to missing data)

**Cannot Verify:**
- Properties 122, 123, 138 (tables don't exist)
- External API calls (no property data to test)
- Property/room scoring (no property data)
- Occupant-based matching (no property data)

### Critical Issues

1. **Database Schema Mismatch:** Code expects tables that don't exist
2. **Missing matching_key Values:** All questions have None for matching_key
3. **No Property Data:** Cannot test property/room recommendations
4. **Incomplete User Profiles:** Only 1 profile exists, test users have no profiles

### Next Steps to Enable Full Functionality

1. **Run migration 001** to create synced_properties, synced_rooms, synced_amenities, synced_allowed_tenants tables
2. **Run migration 003** to create property_recommendations, room_recommendations tables
3. **Populate matching_key** values in questionnaire_questions table
4. **Run data sync** from MSSQL to populate property tables
5. **Test external API** integration with actual property data
6. **Test matching engine** with property occupants

---

**Documentation Method:** Actual code execution with real database  
**Verification Date:** June 13, 2026  
**Database State:** Production-like (missing critical tables)  
**Test Coverage:** Questionnaire system (full), Property system (none)
