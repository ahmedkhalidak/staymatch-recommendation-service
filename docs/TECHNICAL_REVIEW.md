# StayMatch AI Service — Final Technical Review & Optimization

> **Author:** Senior ML Engineer / Recommendation Systems Architect  
> **Date:** 2026-06-10  
> **Scope:** Full review of existing AI service with practical, actionable improvements. No overengineering.

---

## Table of Contents

1. [Architecture Review](#1-architecture-review)
2. [Database Review](#2-database-review)
3. [Questionnaire Review](#3-questionnaire-review)
4. [Final Questionnaire](#4-final-questionnaire)
5. [Feature Engineering Design](#5-feature-engineering-design)
6. [Roommate Matching Design](#6-roommate-matching-design)
7. [Room Compatibility Design](#7-room-compatibility-design)
8. [Property Recommendation Review](#8-property-recommendation-review)
9. [Room Recommendation Review](#9-room-recommendation-review)
10. [Interaction Learning Review](#10-interaction-learning-review)
11. [Weight Optimization](#11-weight-optimization)
12. [Future ML Roadmap](#12-future-ml-roadmap)
13. [Final Step-by-Step Implementation Plan](#13-final-step-by-step-implementation-plan)

---

## 1. Architecture Review

### 1.1 What Works Well

| Component | Status | Notes |
|-----------|--------|-------|
| Modular scorer pipeline | ✅ Good | Clean `BaseScorer` abstraction, easy to add/remove factors |
| Repository pattern | ✅ Good | Data access isolated from business logic |
| Background task recomputation | ✅ Good | Questionnaire answers trigger async recompute |
| Cache with TTL | ✅ Good | 1-hour in-memory check, 24-hour DB persistence |
| Cold-start fallback | ✅ Good | Popularity-based recommendations when no profile exists |
| Diversity enforcement | ✅ Good | Max 3 per city (property), max 2 per property (room) |

### 1.2 Issues Found

| Issue | Severity | Detail |
|-------|----------|--------|
| **Session management** | **HIGH** | Each repository creates its own `Session` in `__init__` via `get_session()`. Multiple repo instances in the same request create separate sessions — no transactional consistency. `get_session()` returns a **new session every call** (not a session factory). |
| **Session leaks** | **MEDIUM** | `PropertyRecommender._check_cache()` opens a session but calls `session.close()` directly instead of using context managers. Several repos never close sessions. |
| **No DI / IoC** | **MEDIUM** | Dependencies are hard-coded in `router.py` via module-level singletons. Testing requires mocking at the module level. |
| **FeedbackScorer.learn_from_interaction()** | **HIGH** | Signature takes `target_type`, `target_id`, `action` but **ignores them all** — it queries all interactions from the last 24h instead. This is misleading. |
| **Interaction endpoint inefficiency** | **MEDIUM** | `/analyze/{user_id}` reads from MSSQL live for every analysis. Should use synced data. |
| **No query timeout** | **LOW** | Long-running recommendation queries could block the server. |
| **API key dependency missing** | **MEDIUM** | The router at `app/api/router.py` defines all endpoints but does NOT include `verify_api_key` as a dependency — auth is documented but not enforced in code. |

### 1.3 Recommended Fixes

```python
# Fix session management — use context managers everywhere
from contextlib import contextmanager

@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage in repository:
class PropertyRepository:
    def get_all_approved(self):
        with session_scope() as session:
            return session.query(SyncedProperty)...all()
```

**Priority fixes (in order):**
1. Add `verify_api_key` dependency to all routes in `router.py`
2. Fix `FeedbackScorer.learn_from_interaction()` signature and behavior
3. Use context managers for all session operations
4. Remove module-level singleton repos in `router.py` — instantiate per-request

---

## 2. Database Review

### 2.1 Missing Indexes

| Table | Missing Index | Why |
|-------|---------------|-----|
| `synced_properties` | Composite: `(is_approved, city, monthly_rent)` | `_prefilter()` filters by all three simultaneously. Current indexes are single-column. |
| `synced_properties` | `(is_approved, property_type)` | `_type_score()` filtering |
| `synced_rooms` | `(is_deleted, capacity_available, property_id)` | Room queries filter by all three |
| `user_feedback_weights` | Unique on `user_id` | Currently only has a plain index, but business logic expects one row per user |
| `user_interactions` | Composite: `(user_id, target_type, target_id, action)` | Interaction analysis queries filter by all four |
| `property_recommendations` | `(user_id, expires_at)` | Cache check needs non-expired entries |
| `roommate_matches` | `(seeker_user_id, expires_at)` | Match results should be filtered by expiry |

### 2.2 Missing Fields

| Table | Field | Type | Why |
|-------|-------|------|-----|
| `synced_properties` | `average_rating` | `Float, nullable` | Needed for review-based scoring. Sync from MSSQL reviews. |
| `synced_properties` | `review_count` | `Integer, default=0` | Needed for confidence-weighted ratings |
| `synced_properties` | `booking_count` | `Integer, default=0` | Needed for popularity scoring |
| `user_profiles` | `is_smoker` | `Boolean, nullable` | Direct smoking preference (questionnaire Q11) |
| `user_profiles` | `sleep_schedule_encoded` | `Integer, nullable` | Pre-encoded sleep schedule (0-3) |
| `user_profiles` | `cleanliness_score` | `Integer, nullable` | Pre-encoded cleanliness (1-4) |
| `user_interactions` | `session_id` | `String(255), nullable` | Group interactions by session for better dwell analysis |

### 2.3 Missing Tables

| Table | Fields | Why |
|-------|--------|-----|
| `sync_log` | `id, table_name, rows_synced, started_at, completed_at, status` | Track sync history for monitoring |
| `recommendation_feedback` | `id, user_id, recommendation_id, was_clicked, was_saved, rating` | Explicit feedback on recommendations shown |

### 2.4 Recommended Schema Changes

```sql
-- 1. Add composite indexes
CREATE INDEX idx_properties_city_rent_approved 
ON synced_properties (is_approved, city, monthly_rent);

CREATE INDEX idx_rooms_available 
ON synced_rooms (is_deleted, capacity_available, property_id);

CREATE UNIQUE INDEX idx_feedback_user_unique 
ON user_feedback_weights (user_id);

CREATE INDEX idx_interactions_analysis 
ON user_interactions (user_id, target_type, target_id, action);

CREATE INDEX idx_property_rec_cache 
ON property_recommendations (user_id, expires_at);

CREATE INDEX idx_roommate_matches_cache 
ON roommate_matches (seeker_user_id, expires_at);

-- 2. Add new fields
ALTER TABLE synced_properties 
ADD COLUMN average_rating FLOAT,
ADD COLUMN review_count INTEGER DEFAULT 0,
ADD COLUMN booking_count INTEGER DEFAULT 0;

-- 3. Add sync_log table
CREATE TABLE sync_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    rows_synced INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running'
);

-- 4. Add recommendation_feedback table
CREATE TABLE recommendation_feedback (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    recommendation_type VARCHAR(20) NOT NULL,  -- 'property' or 'room'
    target_id INTEGER NOT NULL,
    was_clicked BOOLEAN DEFAULT FALSE,
    was_saved BOOLEAN DEFAULT FALSE,
    rating INTEGER,  -- 1-5, nullable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rec_feedback_user ON recommendation_feedback (user_id);
```

---

## 3. Questionnaire Review

### 3.1 Current Questionnaire (16 questions from seed script)

| Q# | Question | Purpose | Verdict |
|----|----------|---------|---------|
| 1 | Current status (Student/Employee/Freelancer/Entrepreneur/Job Seeker) | Occupation matching | **Keep** — critical for lifestyle matching |
| 2 | College/major | Academic background | **Merge into Q1** — only relevant for students |
| 3 | Personality type (Organized/Social/Quiet/Flexible) | Social compatibility | **Keep** — but rename |
| 4 | Sleep schedule (Early bird/Moderate/Late/Night owl) | Lifestyle matching | **Keep** — high importance for roommate harmony |
| 5 | Smoking (Never/Cigarettes/Shisha/Vape/Occasionally) | Lifestyle matching | **Keep** — critical dealbreaker |
| 6 | Visitors frequency | Social compatibility | **Keep** — but rephrase |
| 7 | Noise level preference | Lifestyle matching | **Replace** — overlaps with sleep/personality |
| 8 | Exercise frequency | Lifestyle | **Remove** — low predictive power |
| 9 | Conflict resolution style | Social compatibility | **Keep** — useful for roommate dynamics |
| 10 | Desired interaction frequency | Social compatibility | **Keep** — important for matching |
| 11 | Food/item sharing | Cohabitation practical | **Keep but demote** — lower weight |
| 12 | Hosting friends stance | Social boundaries | **Keep** — important boundary setting |
| 13 | Bill splitting method | Financial compatibility | **Keep** — practical necessity |
| 14 | Rent payment commitment | Financial reliability | **Keep** — high importance |
| 15 | Cleanliness level | Lifestyle matching | **Keep** — critical for shared spaces |
| 16 | Chores division | Cohabitation practical | **Merge with Q15** — same dimension |

### 3.2 Mapping to Requested Questions

The user requested 13 specific questions. Mapping against current:

| Requested | Current | Status |
|-----------|---------|--------|
| 1. Age Group | Missing | **Add** |
| 2. Current Status | Q1 | Already exists |
| 3. Field of Study/Work | Q2 (partial) | **Rewrite** |
| 4. Most Busy Time During Day | Missing | **Add** |
| 5. Typical Sleeping Time | Q4 | Already exists |
| 6. First Action After Returning Home | Missing | **Add** |
| 7. Reaction To Shared Space Mess | Q15 | Already exists |
| 8. How Free Days Are Spent | Missing | **Add** |
| 9. Participation In Group Activities | Q10 | Already exists |
| 10. Preferred Study/Work Environment | Missing | **Add** |
| 11. Smoking Preference and Tolerance | Q5 | Already exists |
| 12. Biggest Shared Housing Frustration | Missing | **Add** |
| 13. Flexibility Toward Different Lifestyles | Q3 | Already exists |

---

## 4. Final Questionnaire

### 4.1 Revised 13 Questions

| # | Question | Type | Options | Matching Weight | Purpose |
|---|----------|------|---------|----------------|---------|
| 1 | What is your age group? | choice | Under 20 / 20-24 / 25-30 / 30+ | 0.08 | Age compatibility |
| 2 | What is your current status? | choice | Student / Employee / Freelancer / Working & Studying | 0.12 | Occupation matching |
| 3 | Field of study or work? | choice | Engineering / Medicine / IT-CS / Business / Arts / Education / Law / Other | 0.03 | Academic/career alignment |
| 4 | Most busy time during the day? | choice | Early morning / Late morning / Afternoon / Evening / Night | 0.08 | Schedule alignment |
| 5 | Typical sleeping time? | choice | Before 10PM / 10PM-12AM / 12AM-2AM / After 2AM | 0.12 | Sleep compatibility |
| 6 | First action after returning home? | choice | Wash/shower / Go to my room / Eat / Start socializing | 0.05 | Hygiene & privacy signal |
| 7 | Reaction to mess in shared spaces? | choice | Clean immediately / Get annoyed but wait / Clean when time / Doesn't bother me | 0.12 | Cleanliness compatibility |
| 8 | How do you spend free days? | choice | At home / Out with friends / Studying/working / Hobbies / Visiting family | 0.03 | Lifestyle matching |
| 9 | Enjoy group activities? | choice | Love it / Sometimes / Rarely / Prefer alone | 0.08 | Social compatibility |
| 10 | Preferred study/work environment? | choice | Quiet private / Moderate / Cafes or public / Flexible | 0.05 | Environment compatibility |
| 11 | Smoking preference and tolerance? | choice | Non-smoker, prefer non-smoker / Non-smoker, okay / Smoker, okay / Smoker, prefer smoker | 0.12 | Critical dealbreaker |
| 12 | Biggest shared housing frustration? | choice | Mess / Noise / Bills / Privacy / Different schedules | 0.07 | Conflict prediction |
| 13 | Flexibility toward different lifestyles? | choice | Very flexible / Somewhat / Prefer similar / Must match | 0.05 | Overall flexibility |

**Total Weight: 1.00**

### 4.2 Category Grouping for Display

| Category | Questions |
|----------|-----------|
| Personal Background | 1 (Age), 2 (Status), 3 (Field) |
| Daily Schedule & Habits | 4 (Busy time), 5 (Sleep), 6 (First action) |
| Lifestyle & Cleanliness | 7 (Mess), 8 (Free days), 10 (Environment) |
| Social & Cohabitation | 9 (Group), 12 (Frustrations), 13 (Flexibility) |
| Critical Preferences | 11 (Smoking) |

---

## 5. Feature Engineering Design

### 5.1 Encoding Scheme

| Q# | Question | Encoding | Reasoning |
|----|----------|----------|-----------|
| 1 | Age group | Under 20=0, 20-24=1, 25-30=2, 30+=3 | Ordered — similarity meaningful |
| 2 | Status | Student=0, Employee=1, Freelancer=2, Working&Studying=3 | Nominal |
| 3 | Field | Engineering=0, Medicine=1, IT/CS=2, Business=3, Arts=4, Education=5, Law=6, Other=7 | Nominal |
| 4 | Busy time | Early morning=0, Late morning=1, Afternoon=2, Evening=3, Night=4 | Ordered |
| 5 | Sleep time | Before 10PM=0, 10PM-12AM=1, 12AM-2AM=2, After 2AM=3 | Ordered |
| 6 | First action | Wash/shower=0, Go to room=1, Eat=2, Socialize=3 | Ordered |
| 7 | Mess reaction | Clean immediately=0, Annoyed but wait=1, Clean when time=2, Doesn't bother=3 | Ordered |
| 8 | Free days | At home=0, Out with friends=1, Studying=2, Hobbies=3, Family=4 | Nominal |
| 9 | Group activities | Love it=0, Sometimes=1, Rarely=2, Alone=3 | Ordered |
| 10 | Work environment | Quiet private=0, Moderate=1, Cafes/public=2, Flexible=3 | Ordered |
| 11 | Smoking | Non-smoker prefers non=0, Non-smoker okay=1, Smoker okay=2, Smoker prefers smoker=3 | **Special dealbreaker** |
| 12 | Frustrations | Mess=0, Noise=1, Bills=2, Privacy=3, Schedules=4 | Nominal |
| 13 | Flexibility | Very flexible=0, Somewhat=1, Prefer similar=2, Must match=3 | Ordered |

### 5.2 Smoking Dealbreaker Logic

```python
def smoking_score(a: int, b: int) -> float:
    diff = abs(a - b)
    if diff <= 1: return 1.0      # Same or compatible
    if diff == 2: return 0.1      # Near-block
    return 0.0                     # Block
```

### 5.3 Feature Encoding Module

Create `app/services/matching/feature_encoding.py` with:
- `QUESTION_WEIGHTS` dict (13 questions, totals 1.00)
- `ORDERED_QUESTIONS` set
- `SMOKING_QID = 11`
- `compute_question_similarity(qid, val_a, val_b)` — handles ordered/nominal/smoking
- `compute_weighted_similarity(answers_a, answers_b)` — full 13-Q weighted similarity with smoking penalty

---

## 6. Roommate Matching Design

### 6.1 Current vs. Recommended Algorithm

**Current:** Simple average of 5 coarse factors with hardcoded weights.

**Recommended:** Weighted feature similarity using 13 per-question encodings:

```
score(u,v) = 0.70 * questionnaire_sim + 0.30 * profile_sim

questionnaire_sim = weighted_similarity(answers_a, answers_b)
profile_sim = 0.4*gender_match + 0.3*occupation_match + 0.3*age_similarity
```

Where `weighted_similarity` uses per-question weights and the smoking penalty multiplier.

### 6.2 Human-Readable Explanation

```python
def generate_explanation(answers_a, answers_b, profile_a, profile_b, score):
    reasons = []
    concerns = []
    # Check sleep (Q5), smoking (Q11), cleanliness (Q7), social (Q9)
    # Build: "88% compatible because both have similar sleeping schedules..."
    return f"{score_pct}% compatible ..."
```

### 6.3 Match Result API Response

```json
{
    "seeker_user_id": "user-123",
    "matches": [{
        "user_id": "user-456",
        "compatibility_score": 0.88,
        "explanation": "88% compatible because both have similar sleeping schedules, share smoking preference, and have matching social preferences.",
        "shared_questions_answered": 13,
        "occupation": "Student",
        "gender": "Female"
    }]
}
```

---

## 7. Room Compatibility Design

### 7.1 Current Aggregation Formula

```python
avg = sum(pairwise_scores) / len(pairwise_scores)
capacity_factor = min(1.0, capacity_available / 3.0)
return avg * (0.7 + 0.3 * capacity_factor)
```

Issues: uses wrong capacity, penalizes all rooms 30%, no min-pooling.

### 7.2 Recommended Aggregation

```python
# 60% worst roommate (min-pooling), 40% average
aggregated = 0.6 * min(pairwise_scores) + 0.4 * avg(pairwise_scores)
empty_bonus = min(0.1, empty_beds * 0.03)
final = min(1.0, aggregated + empty_bonus)
```

**Key insight:** The worst roommate matters more. A room with 2 great + 1 terrible roommate is a terrible room.

### 7.3 Score Thresholds

| Range | Label | Action |
|-------|-------|--------|
| 0.00-0.29 | Low | Filtered out |
| 0.30-0.49 | Marginal | Shown if few options |
| 0.50-0.69 | Moderate | Neutral |
| 0.70-0.84 | Good | Highlighted |
| 0.85-1.00 | Excellent | "Best Match" badge |

---

## 8. Property Recommendation Review

### 8.1 Current Score Factors

Budget(0.30), Location(0.25), Amenities(0.15), Tenant(0.10), Furnished(0.05), Property Type(0.10), Recency(0.00), Questionnaire(0.05)

### 8.2 Issues

1. No review/rating factor
2. No popularity signal
3. Recency weight is 0 (unused)
4. Cold-start is only popularity-based
5. Hard prefilter excludes cross-city properties

### 8.3 Recommended Changes

```python
PROPERTY_WEIGHTS = {
    "budget": 0.25, "location": 0.20, "amenities": 0.12,
    "tenant": 0.10, "furnished": 0.05, "property_type": 0.08,
    "recency": 0.05, "questionnaire": 0.05, "ratings": 0.10,
}
```

Add `RatingsScorer` with Bayesian averaging. Soft prefilter (no hard city exclusion). Improve cold-start with recency + popularity + city diversity.

---

## 9. Room Recommendation Review

### 9.1 Current Score Factors

Budget(0.25), Location(0.20), Capacity(0.15), Amenities(0.10), Tenant(0.10), Furnished(0.05), Room Type(0.10), Recency(0.05)

### 9.2 Issues

1. No roommate compatibility influence
2. Capacity scoring inverted (more empty = higher score)
3. Room type only checks bathroom
4. No property-level reputation

### 9.3 Recommended Changes

```python
ROOM_WEIGHTS = {
    "budget": 0.20, "location": 0.15, "capacity": 0.08,
    "amenities": 0.10, "tenant": 0.08, "furnished": 0.05,
    "room_type": 0.10, "recency": 0.04,
    "roommate_compat": 0.15, "property_rating": 0.05,
}
```

Add roommate compatibility via CompatibilityEngine, improve capacity scoring (fill-ratio based), expand room type (balcony, window, ensuite).

---

## 10. Interaction Learning Review

### 10.1 Current Weights

```
dwell_high(30s+) = 3.0, saved = 2.5, liked = 2.0, contacted = 2.0,
dwell_medium(10s+) = 1.5, viewed = 1.0, skipped = 0.3
```

### 10.2 Issues

1. Dwell over-weighted (3.0 = same as saving 3 properties)
2. Skipped too harsh (0.3)
3. No time decay
4. learn_from_interaction() ignores its parameters
5. Analysis queries MSSQL live

### 10.3 Recommended Weights

```python
INTERACTION_WEIGHTS = {
    "saved": 5.0, "liked": 4.0, "contacted": 5.0,
    "dwell_high": 2.5, "dwell_medium": 1.5,
    "viewed": 1.0, "skipped": 0.5,
}
```

### 10.4 Time Decay Function

```python
def time_weight(created_at):
    days = (now - created_at).days
    return 1.0 if days <= 1 else 0.8 if days <= 7 else 0.5 if days <= 30 else 0.2 if days <= 90 else 0.05
```

---

## 11. Weight Optimization

### 11.1 Property Weights

| Factor | Current | Recommended | Change |
|--------|---------|-------------|--------|
| budget | 0.30 | 0.25 | -0.05 |
| location | 0.25 | 0.20 | -0.05 |
| amenities | 0.15 | 0.12 | -0.03 |
| tenant | 0.10 | 0.10 | same |
| furnished | 0.05 | 0.05 | same |
| property_type | 0.10 | 0.08 | -0.02 |
| recency | 0.00 | 0.05 | +0.05 |
| questionnaire | 0.05 | 0.05 | same |
| ratings | 0.00 | 0.10 | +0.10 |

### 11.2 Room Weights

| Factor | Current | Recommended | Change |
|--------|---------|-------------|--------|
| budget | 0.25 | 0.20 | -0.05 |
| location | 0.20 | 0.15 | -0.05 |
| capacity | 0.15 | 0.08 | -0.07 |
| amenities | 0.10 | 0.10 | same |
| tenant | 0.10 | 0.08 | -0.02 |
| furnished | 0.05 | 0.05 | same |
| room_type | 0.10 | 0.10 | same |
| recency | 0.05 | 0.04 | -0.01 |
| roommate_compat | 0.00 | 0.15 | +0.15 |
| property_rating | 0.00 | 0.05 | +0.05 |

### 11.3 Matching Weights

Replaced 5-category system with 13 per-question weights (see §5) plus profile component (gender 12%, occupation 9%, age 9% within 30% profile sub-weight).

---

## 12. Future ML Roadmap

### 12.1 Do NOT Implement ML Now

Rule-based system is appropriate for graduation project. ML needs sufficient logged data.

### 12.2 Data Requirements

| Source | Min Records | Timeframe |
|--------|-------------|-----------|
| Interactions | 10,000+ | 3+ months |
| Bookings | 1,000+ | 6+ months |
| Reviews | 500+ | 6+ months |
| Match outcomes | 500+ pairs | 6+ months |

### 12.3 Recommended ML Models

**Model A:** XGBoost for property score prediction
**Model B:** Collaborative filtering embeddings (TruncatedSVD)
**Model C:** LightGBM for match acceptance prediction
**Model D:** Sentence Transformers for content embeddings

### 12.4 Training Phases

```
Phase 3A (Month 1-2): XGBoost property scoring
Phase 3B (Month 3-4): Collaborative filtering
Phase 3C (Month 5-6): Match acceptance prediction
Phase 4 (Ongoing): Full personalization pipeline
```

---

## 13. Final Step-by-Step Implementation Plan

### Phase 1: Working System (Weeks 1-3) — 11 HIGH priority tasks

| # | Task | Priority |
|---|------|----------|
| 1.1 | Add API key dependency to all routes | HIGH |
| 1.2 | Fix session management (context managers) | HIGH |
| 1.3 | Fix FeedbackScorer.learn_from_interaction() | HIGH |
| 1.4 | Update seed questionnaire to 13 questions | HIGH |
| 1.5 | Create feature_encoding.py module | HIGH |
| 1.6 | Rewrite matching engine with per-question weights | HIGH |
| 1.7 | Add smoking dealbreaker logic | HIGH |
| 1.8 | Add human-readable explanation generation | HIGH |
| 1.9 | Fix room aggregation (min-pooling) | MEDIUM |
| 1.10 | Update conftest.py with new mocks | MEDIUM |
| 1.11 | Update matching tests | MEDIUM |

### Phase 2: Improved Ranking (Weeks 4-5) — 9 tasks

| # | Task | Priority |
|---|------|----------|
| 2.1 | Add rating/review fields to synced_properties | HIGH |
| 2.2 | Create RatingsScorer | HIGH |
| 2.3 | Update property weights | HIGH |
| 2.4 | Update room weights | HIGH |
| 2.5 | Improve budget scorer (graduated) | MEDIUM |
| 2.6 | Activate recency factor | MEDIUM |
| 2.7 | Soft prefilter properties | MEDIUM |
| 2.8 | Expand room type scorer | MEDIUM |
| 2.9 | Add roommate compat to room scoring | MEDIUM |

### Phase 3: Interaction Learning (Weeks 6-7) — 5 tasks

| # | Task | Priority |
|---|------|----------|
| 3.1 | Add time decay to interaction weights | MEDIUM |
| 3.2 | Update interaction weight values | MEDIUM |
| 3.3 | Fix analyzer to use synced data | MEDIUM |
| 3.4 | Improve user classifier | LOW |
| 3.5 | Add recommendation_feedback table | LOW |

### Phase 4: Database Optimization (Week 8) — 5 tasks

| # | Task | Priority |
|---|------|----------|
| 4.1 | Add composite indexes | MEDIUM |
| 4.2 | Add unique constraint on feedback weights | MEDIUM |
| 4.3 | Add sync_log table | LOW |
| 4.4 | Add property fields (avg_rating, review_count) | MEDIUM |
| 4.5 | Add expired recommendation cleanup | LOW |

### Summary

| Priority | Count | Timeline |
|----------|-------|----------|
| HIGH | 11 tasks | Phase 1 (Weeks 1-3) |
| MEDIUM | 11 tasks | Phase 2-3 (Weeks 4-7) |
| LOW | 5 tasks | Phase 4 (Week 8) |
| **Total** | **27 tasks** | **8 weeks** |

---

## Appendix: Key Formulas

### Final Matching Formula

```
score(u,v) = 0.70 × questionnaire_sim + 0.30 × profile_sim

questionnaire_sim = [Σ w_q × sim_q / Σ w_q] × smoking_penalty
  - w_q = per-question weight
  - sim_q = 1 - |enc_u - enc_v| / max_val  (ordered)
            1 if enc_u == enc_v else 0      (nominal)
  - smoking_penalty = 1.0 (diff≤1), 0.1 (diff=2), 0.0 (diff≥3)

profile_sim = 0.4 × gender_match + 0.3 × occupation_match + 0.3 × age_similarity
```

### Final Room Aggregation

```
room_score = 0.6 × min(pairwise) + 0.4 × avg(pairwise) + min(0.1, empty_beds × 0.03)
```

### Final Property Score

```
total = 0.25×budget + 0.20×location + 0.12×amenities + 0.10×tenant
      + 0.05×furnished + 0.08×property_type + 0.05×recency
      + 0.05×questionnaire + 0.10×ratings
```

### Final Room Score

```
total = 0.20×budget + 0.15×location + 0.08×capacity + 0.10×amenities
      + 0.08×tenant + 0.05×furnished + 0.10×room_type + 0.04×recency
      + 0.15×roommate_compat + 0.05×property_rating
```

---

## 14. Booking-Based Occupant Identification (Clarification)

### 14.1 Official Rule — How Current Occupants Are Identified

Roommate matching must use **active approved bookings** to determine who currently occupies each room. This is not based on questionnaire answer existence — it is based on the main ASP.NET platform's `Bookings` table.

**Rule:**

```sql
-- Current Occupants = users with approved bookings for the same room
-- where the booking is still active (end date >= today)

SELECT UserId
FROM Bookings
WHERE RoomId = @room_id
  AND Status = 'Approved'
  AND EndDate >= CURRENT_DATE
```

**Why this matters:**
- The `Bookings` table is the **source of truth** for who lives where
- Matching against non-occupants who happen to have answered the questionnaire is incorrect
- A user may have answered the questionnaire but no longer live in that room
- A room may have occupants who never answered the questionnaire (fallback to profile-only matching)

### 14.2 Data Source Options

Two approaches to access the `Bookings` table:

**Option A: Sync to PostgreSQL (preferred for production)**

Add a synced copy of the `Bookings` table to the AI database. Follows the same pattern as `synced_properties`, `synced_rooms`, etc.

```sql
CREATE TABLE synced_bookings (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    property_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_synced_bookings_room ON synced_bookings (room_id, status, end_date);
CREATE INDEX idx_synced_bookings_user ON synced_bookings (user_id);
```

**Option B: Live MSSQL query (simpler — recommended for graduation project)**

Query the `Bookings` table directly from MSSQL when computing matches, using a new function in `mssql_reader.py`:

```python
def get_current_room_occupants(room_id: int) -> list[dict]:
    """Get current occupants of a room based on active approved bookings in MSSQL."""
    engine = get_mssql_engine()
    if not engine:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT b.UserId, b.StartDate, b.EndDate
                    FROM Bookings b
                    WHERE b.RoomId = :room_id
                      AND b.Status = 'Approved'
                      AND b.EndDate >= CAST(GETDATE() AS DATE)
                """),
                {"room_id": room_id}
            ).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error("get_current_room_occupants(%s) failed: %s", room_id, e)
        return []
```

**Decision: Option B (Live MSSQL) is recommended** because:
- Bookings data changes frequently — syncing adds stale data risk
- Existing `mssql_reader.py` already handles live reads
- No migration needed
- Simpler implementation

### 14.3 Updated Matching Flow

```
1. User requests room recommendations.

2. Retrieve room candidates (from synced_rooms).

3. For EACH room:

   a. Query MSSQL Bookings:
      SELECT UserId FROM Bookings 
      WHERE RoomId = ? AND Status = 'Approved' AND EndDate >= TODAY

   b. For EACH occupant UserId found:
      
      - Check if occupant has questionnaire answers in PostgreSQL
      - If YES: compute full pairwise score (13-Q similarity + profile)
      - If NO: compute profile-only score (gender + occupation + age)
        -> profile-only = 0.4*gender + 0.3*occupation + 0.3*age
        -> This yields a neutral-to-moderate score (typically 0.4-0.7)
      
      - Store: {user_id, score, shared_questions_answered}

   c. If NO occupants found (room is empty):
      -> roommate_compat_score = 0.65 (neutral, with empty room bonus)

   d. If occupants found:
      -> pairwise_scores = [occupant.score for each occupant]
      -> room_score = 0.6 * min(pairwise_scores) + 0.4 * avg(pairwise_scores)
      -> empty_beds = max(0, room.capacity - len(occupants))
      -> room_score += min(0.1, empty_beds * 0.03)
      -> room_score = min(1.0, room_score)

4. Room ranking considers:
   - Room features (budget, capacity, room_type, furnished)
   - Property features (location, amenities, ratings)
   - Tenant restrictions (from synced_allowed_tenants)
   - Roommate compatibility score (from step 3)
```

### 14.4 Updated CompatibilityEngine Implementation Changes

The key changes to `app/services/matching/compatibility_engine.py`:

1. **Replace** `_get_answers_as_dict` occupant retrieval with `get_current_room_occupants()` from MSSQL
2. **Add** `_profile_only_score()` fallback for occupants without questionnaire answers
3. **Update** `_aggregate_room_score()` to use total capacity instead of `capacity_available` for empty bed calculation
4. **Remove** the old logic that queried `UserProfile` for all users except seeker

```python
# Key structural change in compute_for_user:

def compute_for_user(self, seeker_id: str) -> dict:
    seeker_answers = self._get_answers_as_dict(seeker_id)
    seeker_profile = self._get_profile(seeker_id)
    
    if not seeker_answers and not seeker_profile:
        return {"status": "skipped", "reason": "no data", "matches": []}
    
    rooms = self._get_available_rooms()
    matches = []
    
    for room in rooms:
        # --- CHANGED: Get occupants from BOOKINGS instead of all users ---
        occupants = get_current_room_occupants(room.id)
        
        if not occupants:
            # Empty room
            matches.append({
                "room_id": room.id,
                "property_id": room.property_id,
                "room_compatibility_score": 0.65,
                "roommate_count": 0,
                "empty_beds": room.capacity or 1,
                "explanation": "Room is currently empty.",
            })
            continue
        
        pairwise_scores = []
        roommate_details = []
        
        for occ in occupants:
            occupant_user_id = str(occ["user_id"])
            if occupant_user_id == seeker_id:
                continue
            
            occ_answers = self._get_answers_as_dict(occupant_user_id)
            occ_profile = self._get_profile(occupant_user_id)
            
            if occ_answers and seeker_answers:
                score = self._compute_pairwise(seeker_answers, occ_answers, seeker_profile, occ_profile)
            else:
                # --- NEW: Profile-only fallback ---
                score = self._profile_only_score(seeker_profile, occ_profile)
            
            if score >= 0.3:
                pairwise_scores.append(score)
                roommate_details.append({
                    "user_id": occupant_user_id,
                    "score": round(score, 4),
                    "matched_via": "questionnaire" if occ_answers else "profile_only",
                })
        
        if not pairwise_scores:
            continue
        
        # Aggregate using the same min-pooling formula
        room_result = self._aggregate_room_score(pairwise_scores, room.capacity or 1, len(pairwise_scores))
        # ... save and append
```

### 14.5 Updated Room Recommender Integration

The `RoomRecommender` must use `CompatibilityEngine` with booking-based occupants:

```python
# New method in RoomRecommender:

def _get_roommate_score(self, user_id: str, room) -> float:
    """Get roommate compatibility score using booking-based occupants."""
    occupants = get_current_room_occupants(room.id)
    if not occupants:
        return 0.65  # Empty room
    
    seeker_answers = self._get_answers_as_dict(user_id)
    seeker_profile = self._get_profile(user_id)
    
    if not seeker_answers and not seeker_profile:
        return 0.5  # No data
    
    pairwise_scores = []
    for occ in occupants:
        occ_user_id = str(occ["user_id"])
        if occ_user_id == user_id:
            continue
        occ_answers = self.engine._get_answers_as_dict(occ_user_id)
        occ_profile = self.engine._get_profile(occ_user_id)
        
        if occ_answers and seeker_answers:
            score = self.engine._compute_pairwise(seeker_answers, occ_answers, seeker_profile, occ_profile)
        else:
            score = self.engine._profile_only_score(seeker_profile, occ_profile)
        
        if score >= 0.3:
            pairwise_scores.append(score)
    
    if not pairwise_scores:
        return 0.5
    
    aggregated = 0.6 * min(pairwise_scores) + 0.4 * (sum(pairwise_scores) / len(pairwise_scores))
    empty_beds = max(0, (room.capacity or 1) - len(pairwise_scores))
    empty_bonus = min(0.1, empty_beds * 0.03)
    return min(1.0, aggregated + empty_bonus)
```

### 14.6 Batch Optimization for Room Recommendations

When recommending rooms, querying MSSQL per-room is expensive. Use a batch query:

```python
# In mssql_reader.py — batch version

def get_room_occupants_batch(room_ids: list[int]) -> dict[int, list[dict]]:
    """Get occupants for multiple rooms in one query.
    Returns: {room_id: [{user_id, start_date, end_date}, ...]}
    """
    if not room_ids:
        return {}
    engine = get_mssql_engine()
    if not engine:
        return {}
    ids = list(set(room_ids))
    placeholders = ",".join(f":id_{i}" for i in range(len(ids)))
    params = {f"id_{i}": v for i, v in enumerate(ids)}
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT b.RoomId, b.UserId, b.StartDate, b.EndDate
                FROM Bookings b
                WHERE b.RoomId IN ({placeholders})
                  AND b.Status = 'Approved'
                  AND b.EndDate >= CAST(GETDATE() AS DATE)
            """),
            params
        ).mappings().all()
    result = {}
    for r in rows:
        rid = r["RoomId"]
        if rid not in result:
            result[rid] = []
        result[rid].append({
            "user_id": r["UserId"],
            "start_date": r["StartDate"],
            "end_date": r["EndDate"],
        })
    return result
```

Then in `RoomRecommender.recommend()`, pre-fetch all occupants before the scoring loop:

```python
def recommend(self, user, rooms, context=None):
    # ... existing cache check ...
    
    # --- NEW: Batch pre-fetch all occupants ---
    room_ids = [r.id for r in rooms]
    all_occupants = get_room_occupants_batch(room_ids)
    
    scored = []
    for room in rooms:
        occupants = all_occupants.get(room.id, [])
        # Use occupants for roommate scoring...
```

### 14.7 Updated Score Thresholds (Booking-Based)

| Occupants Found | Score Range | Meaning |
|----------------|-------------|---------|
| 0 (empty room) | 0.65 | Neutral — no one to conflict with |
| 1+ with all >= 0.7 | 0.70-1.00 | Compatible with all roommates |
| 1+ with mixed scores | 0.40-0.69 | Some compatibility, some tension |
| 1+ with any < 0.3 | < 0.40 | Filtered out — incompatible roommate |

---

## 15. Implementation Plan Addendum — Booking-Based Occupant Identification

### 15.1 New Tasks Added to Phase 1

| # | Task | Priority | Dependencies |
|---|------|----------|-------------|
| 1.12 | Add `get_current_room_occupants()` to `app/services/mssql_reader.py` | **HIGH** | None |
| 1.13 | Add `get_room_occupants_batch()` for batch room recommendations | **HIGH** | 1.12 |
| 1.14 | Update `CompatibilityEngine.compute_for_user()` to use booking-based occupants | **HIGH** | 1.12 |
| 1.15 | Add `_profile_only_score()` fallback for occupants without questionnaire answers | **HIGH** | 1.14 |
| 1.16 | Update `RoomRecommender._get_roommate_score()` to use booking-based occupants | **HIGH** | 1.13 |
| 1.17 | Add `_get_answers_as_dict()` helper to `RoomRecommender` for reuse | **MEDIUM** | 1.16 |
| 1.18 | Add MSSQL availability check — graceful fallback if MSSQL is down | **MEDIUM** | 1.12 |

### 15.2 Updated Task Count

| Phase | Tasks | HIGH | MEDIUM | LOW |
|-------|-------|------|--------|-----|
| **Phase 1** | 18 (+7 new) | 15 | 3 | 0 |
| **Phase 2** | 9 | 4 | 5 | 0 |
| **Phase 3** | 5 | 0 | 3 | 2 |
| **Phase 4** | 5 | 0 | 3 | 2 |
| **Total** | **37** | **19** | **14** | **4** |

Timeline: **8 weeks**

### 15.3 Complete Matching Flow Diagram

```
                    ROOM MATCHING FLOW
                    ==================

  GET /recommend/rooms/{user_id}
           |
           v
  Retrieve available rooms (synced_rooms)
           |
           v
  Batch query MSSQL Bookings:
    SELECT RoomId, UserId FROM Bookings
    WHERE RoomId IN (...) 
      AND Status = 'Approved'
      AND EndDate >= TODAY
           |
           v
  For EACH room:
           |
     +-----+-----+
     |           |
     v           v
  No occupants  Occupants found
     |           |
     v           v
  0.65 score    For EACH occupant:
                   |
             +-----+-----+
             |           |
             v           v
        Has Q answers  No Q answers
             |           |
             v           v
        13-Q matching  Profile-only
        (0.50-1.00)    (0.40-0.70)
             |           |
             +-----+-----+
                   |
                   v
            pairwise_scores[]
                   |
                   v
            room_score = 0.6*min + 0.4*avg + empty_bonus
                   |
                   v
            Final ranking:
            0.20*budget + 0.15*location + 0.08*capacity +
            0.10*amenities + 0.08*tenant + 0.05*furnished +
            0.10*room_type + 0.04*recency +
            0.15*roommate_compat + 0.05*property_rating
```

---

*End of Technical Review. All recommendations are practical, implementable within 8 weeks, and suitable for a graduation project.*