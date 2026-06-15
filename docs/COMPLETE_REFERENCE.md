# StayMatch Recommendation Service — Complete Technical Reference

> Full documentation of the StayMatch recommendation engine, API, data model, scoring pipeline, deployment, and testing.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
4. [Directory Structure](#4-directory-structure)
4. [Configuration](#4-configuration)
5. [Security](#5-security)
6. [Database](#6-database)
   - [Connection & Session Management](#61-connection--session-management)
   - [Model Reference](#62-model-reference)
   - [Migrations](#63-migrations)
7. [API Endpoints](#7-api-endpoints)
   - [Health](#71-health)
   - [Sync](#72-sync)
   - [Recommendations](#73-recommendations)
   - [Matching](#74-matching)
   - [Users](#75-users)
   - [Questionnaire](#76-questionnaire)
   - [Interactions](#77-interactions)
   - [Analysis](#78-analysis)
   - [Admin / A/B Testing](#79-admin--ab-testing)
8. [Schemas (Pydantic)](#8-schemas-pydantic)
9. [Scoring Pipeline](#9-scoring-pipeline)
   - [BaseScorer](#91-basescorer)
   - [BudgetScorer](#92-budgetscorer)
   - [LocationScorer](#93-locationscorer)
   - [AmenityScorer](#94-amenityscorer)
   - [TenantScorer](#95-tenantscorer)
   - [QuestionnaireScorer](#96-questionnairescorer)
   - [FeedbackScorer](#97-feedbackscorer)
10. [Ranking & Weights](#10-ranking--weights)
    - [Ranker](#101-ranker)
    - [Default Weights](#102-default-weights)
11. [Recommenders](#11-recommenders)
    - [PropertyRecommender](#111-propertyrecommender)
    - [RoomRecommender](#112-roomrecommender)
12. [Compatibility Engine (Matching)](#12-compatibility-engine-matching)
13. [Data Sync Service](#13-data-sync-service)
14. [Interaction Analyzer & Classification](#14-interaction-analyzer--classification)
15. [Location Heatmap](#15-location-heatmap)
16. [Preferences Bridge](#16-preferences-bridge)
17. [Questionnaire Content](#17-questionnaire-content)
18. [Repositories](#18-repositories)
19. [Utilities](#19-utilities)
20. [Testing](#20-testing)
21. [Deployment](#21-deployment)
22. [Common Commands](#22-common-commands)

---

## 1. Project Overview

**StayMatch Recommendation Service** is a FastAPI-based microservice that provides personalized property and room recommendations for a Egyptian housing platform. It also handles roommate matching, user profiling via questionnaires, interaction-based preference learning, and periodic data synchronization from a legacy MSSQL database.

- **Language:** Python 3.11
- **Framework:** FastAPI 0.104
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL (Neon) + MSSQL (sync source, read-only)
- **Migrations:** Alembic
- **Testing:** pytest (all mocks, no real database)
- **Deployment:** Docker on Railway

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
│                                                         │
│  ┌─────────────┐  ┌──────────────────────────────────┐  │
│  │  API Layer   │  │        Scoring Pipeline          │  │
│  │  (router.py) │  │  ┌──────┐┌──────┐┌───────────┐  │  │
│  │  + health.py │  │  │Budget││Loc.  ││Amenity    │  │  │
│  └──────┬───────┘  │  └──────┘└──────┘└───────────┘  │  │
│         │          │  ┌──────┐┌──────┐┌───────────┐  │  │
│  ┌──────▼───────┐  │  │Tenant││Quest.││Feedback   │  │  │
│  │ Repositories  │  │  └──────┘└──────┘└───────────┘  │  │
│  │ (data access) │  │         ┌────────┐              │  │
│  └──────┬───────┘  │         │ Ranker │              │  │
│         │          │         └───┬────┘              │  │
│  ┌──────▼───────┐  │  ┌──────────▼───────────┐       │  │
│  │   Database   │  │  │ PropertyRecommender  │       │  │
│  │  (PostgreSQL)│  │  │ + RoomRecommender    │       │  │
│  └──────────────┘  │  └──────────────────────┘       │  │
│                    │                                  │  │
│  ┌──────────────┐  │  ┌──────────────────────────┐   │  │
│  │ MSSQL (Sync) │  │  │ CompatibilityEngine     │   │  │
│  │ (read-only)  │  │  │ (Roommate Matching)     │   │  │
│  └──────────────┘  │  └──────────────────────────┘   │  │
│                    │                                  │  │
│  ┌──────────────┐  │  ┌──────────────────────────┐   │  │
│  │ Interaction  │  │  │ InteractionAnalyzer     │   │  │
│  │ Logging      │──┼─▶│ + UserClassifier        │   │  │
│  └──────────────┘  │  └──────────────────────────┘   │  │
└─────────────────────────────────────────────────────────┘
```

**Data flow:**
1. **Startup** → Check DB connection, sync chatbot preferences (`PreferencesBridge.sync_all()`)
2. **Sync** → Read from MSSQL (`Properties`, `Rooms`, `Amenities`, `AllowedTenants`, `AspNetUsers`), upsert into PostgreSQL
3. **Recommendations** → Prefilter → Score (7 factors) → Rank → Diversity (max 3/city) → Cache
4. **Matching** → Load seeker answers → Find roommates → Pairwise similarity → Aggregate → Store (24h TTL)
5. **Interactions** → Log dwell/save/like/skip → Analyze → Infer preferences → Update feedback weights

---

## 3. Directory Structure

```
├── .env                        # Active environment variables
├── .env.example                # Template for env vars
├── .gitignore
├── .kilo/                      # Kilo agent manager workspace data
├── AGENTS.md                   # Agent guide for AI coding assistants
├── Dockerfile                  # Docker build (python:3.11-slim, ODBC 17 + FreeTDS)
├── GPDataBaseMain_net.json     # MSSQL schema reference dump
├── README.md                   # Full project README
├── alembic.ini                 # Alembic configuration
├── railway.toml                # Railway deploy config
├── requirements.txt            # Python dependencies
│
├── alembic/
│   ├── env.py                  # Alembic environment (auto-discovers models)
│   ├── script.py.mako          # Migration template
│   └── versions/               # 8 migration files (001–008)
│
├── app/                        # Main application package
│   ├── __init__.py
│   ├── main.py                 # FastAPI entrypoint + lifespan
│   ├── config.py               # Pydantic Settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py           # GET /health
│   │   └── router.py           # All business endpoints (~486 lines)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── security.py         # API key verification
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py          # Engine + session factories (PG + MSSQL)
│   │   └── models/
│   │       ├── __init__.py     # Imports all models into Base.metadata
│   │       ├── base.py         # DeclarativeBase
│   │       ├── property.py     # SyncedProperty, SyncedRoom, SyncedAmenity, SyncedAllowedTenant
│   │       ├── user.py         # UserProfile, QuestionnaireCategory, QuestionnaireQuestion,
│   │       │                   #   UserQuestionnaireAnswer, UserSearchPreference
│   │       ├── recommendation.py  # ScoringWeight, UserFeedbackWeight, PropertyRecommendation,
│   │       │                      #   RoomRecommendation, RoommateMatch, UserInteraction
│   │       └── matching.py     # PropertyEmbedding, UserEmbedding
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── property_repo.py    # 7 repository classes (~258 lines)
│   │   └── weights_repo.py     # WeightRepository + FeedbackRepository (~54 lines)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── recommendation.py   # Pydantic request/response schemas (~54 lines)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   ├── base_scorer.py          # Abstract BaseScorer
│   │   │   ├── budget_scorer.py        # BudgetScorer
│   │   │   ├── location_scorer.py      # LocationScorer
│   │   │   ├── amenity_scorer.py       # AmenityScorer
│   │   │   ├── tenant_scorer.py        # TenantScorer
│   │   │   ├── questionnaire_scorer.py # QuestionnaireScorer
│   │   │   └── feedback_scorer.py      # FeedbackScorer
│   │   │
│   │   ├── ranking/
│   │   │   ├── __init__.py
│   │   │   └── ranker.py               # Ranker (weighted sum)
│   │   │
│   │   ├── recommendation/
│   │   │   ├── __init__.py
│   │   │   └── property_recommender.py # PropertyRecommender + RoomRecommender (~301 lines)
│   │   │
│   │   ├── matching/
│   │   │   ├── __init__.py
│   │   │   └── compatibility_engine.py # CompatibilityEngine (~177 lines)
│   │   │
│   │   ├── sync/
│   │   │   ├── __init__.py
│   │   │   └── data_sync.py            # DataSyncService (~318 lines)
│   │   │
│   │   ├── interaction_analyzer.py     # InteractionAnalyzer + UserClassifier + similar_props
│   │   ├── location_heatmap.py         # LocationHeatmap
│   │   ├── mssql_reader.py             # Direct MSSQL reads
│   │   ├── preferences_bridge.py       # PreferencesBridge
│   │   └── questionnaire_service.py    # QuestionnaireService
│   │
│   └── utils/
│       ├── __init__.py
│       ├── location.py         # geo_distance, governorate_center, GOVERNORATE_CENTERS
│       └── weights.py          # PROPERTY_WEIGHTS, ROOM_WEIGHTS, MATCHING_WEIGHTS
│
├── docs/                       # Documentation (this file lives here)
│   └── COMPLETE_REFERENCE.md
│
├── scripts/
│   ├── __init__.py
│   ├── seed_questionnaire.py   # Seeds 16 questions across 4 categories
│   └── sync_data.py            # CLI trigger for full MSSQL sync
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Mock classes + fixtures (10 test files)
    ├── test_budget_scorer.py         # 11 tests
    ├── test_location_scorer.py       # 5 tests
    ├── test_amenity_scorer.py        # 5 tests
    ├── test_tenant_scorer.py         # 8 tests
    ├── test_ranker.py                # 7 tests
    ├── test_matching.py              # 8 tests
    ├── test_schemas.py               # 5 tests
    ├── test_feedback_scorer.py       # 3 tests
    ├── test_interaction_analyzer.py  # 13 tests
    └── test_utils.py                 # 8 tests
```

---

## 4. Configuration

**File:** `app/config.py`

Uses `pydantic-settings` to read from environment variables (`.env` file).

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | `str` | — | PostgreSQL connection string (required) |
| `MSSQL_CONNECTION_STRING` | `str` | `""` | Full ODBC connection string for MSSQL |
| `DB_HOST` | `str` | `""` | MSSQL host (fallback if no full string) |
| `DB_PORT` | `int` | `1433` | MSSQL port |
| `DB_NAME` | `str` | `""` | MSSQL database name |
| `DB_USER` | `str` | `""` | MSSQL username |
| `DB_PASSWORD` | `str` | `""` | MSSQL password |
| `SYNC_INTERVAL_MINUTES` | `int` | `5` | How often to sync from MSSQL |
| `API_KEY` | `str` | `""` | API key for endpoint auth (empty = skip auth) |
| `SCORING_WEIGHTS_OVERRIDE` | `Optional[str]` | `None` | JSON override for scoring weights |
| `LOG_LEVEL` | `str` | `"INFO"` | Logging level |

**Usage pattern:** Settings are loaded on-the-fly — no shared singleton:

```python
from app.config import Settings
settings = Settings()
```

---

## 5. Security

**File:** `app/core/security.py`

All endpoints require `X-API-Key` header verification via the `verify_api_key` dependency:

```python
async def verify_api_key(x_api_key: str = Header(None)):
    expected = get_api_key()  # lazy-loaded from Settings
    if not expected:
        return  # auth skipped when API_KEY is empty
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Note:** While `security.py` implements the logic, the router at `app/api/router.py` must explicitly include `verify_api_key` as a dependency on each route or globally.

---

## 6. Database

### 6.1 Connection & Session Management

**File:** `app/database/session.py`

| Function | Description |
|----------|-------------|
| `get_engine()` | Creates/maintains singleton SQLAlchemy engine for PostgreSQL. Retries up to 5 times on connection failure (`_wait_for_db`). |
| `get_session()` | Returns a new `Session` from the singleton session factory. |
| `get_mssql_engine()` | Creates MSSQL engine via `pyodbc` (FreeTDS/ODBC 17). Falls back from full connection string to individual host/port/db/user/password fields. Returns `None` if MSSQL is not configured. |
| `test_connection()` | Pings PostgreSQL with `SELECT 1`. Returns `True`/`False`. |

### 6.2 Model Reference

**Base class:** `app/database/models/base.py` — `class Base(DeclarativeBase): pass`

---

#### `SyncedProperty` → `synced_properties`

Read-only copy from MSSQL `Properties` table.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `owner_id` | `String(255)` | |
| `name` | `Text` | |
| `description` | `Text` | |
| `street` | `Text` | |
| `city` | `Text` | |
| `government` | `Text` | Egyptian governorate |
| `latitude` | `DOUBLE_PRECISION` | |
| `longitude` | `DOUBLE_PRECISION` | |
| `property_type` | `Integer NOT NULL` | `0` = full apartment, `1` = shared/room |
| `monthly_rent` | `DOUBLE_PRECISION` | |
| `deposit` | `DOUBLE_PRECISION` | |
| `size` | `DOUBLE_PRECISION` | Area in m² |
| `number_of_bedrooms` | `Integer` | |
| `number_of_living_rooms` | `Integer` | |
| `total_rooms` | `Integer` | |
| `available_rooms` | `Integer` | |
| `furnished` | `Boolean` | |
| `minimum_stay` | `Integer` | Minimum lease in months |
| `available_from` | `DateTime` | |
| `is_approved` | `Boolean NOT NULL` | |
| `created_at` | `DateTime` | |
| `last_modified` | `DateTime` | |
| `synced_at` | `DateTime` | When last synced from MSSQL |

**Relationships:** `rooms` (one-to-many), `amenities` (uselist=False), `allowed_tenants`
**Indexes:** city, government, property_type, monthly_rent, is_approved, (latitude, longitude), synced_at

---

#### `SyncedRoom` → `synced_rooms`

Read-only copy from MSSQL `Rooms` table.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `property_id` | `Integer FK → synced_properties.id` | |
| `room_name` | `Text` | |
| `month_rent` | `DOUBLE_PRECISION` | |
| `deposit` | `DOUBLE_PRECISION` | |
| `capacity` | `Integer` | Total beds |
| `capacity_available` | `Integer` | Currently available beds |
| `furnished` | `Boolean` | |
| `ensuite_bathroom` | `Boolean` | |
| `shared_bathroom` | `Boolean` | |
| `balcony` | `Boolean` | |
| `window` | `Boolean` | |
| `pets_allowed` | `Boolean` | |
| `minimum_stay` | `Integer` | |
| `available_from` | `DateTime` | |
| `is_deleted` | `Boolean NOT NULL` | Soft delete flag |
| `created_at` | `DateTime` | |
| `synced_at` | `DateTime` | |

**Relationships:** `property` (back_populates="rooms"), `allowed_tenants`

---

#### `SyncedAmenity` → `synced_amenities`

Read-only copy from MSSQL `PropertyAmenities` table. One row per property.

| Column | Type |
|--------|------|
| `property_id` | `Integer PK, FK → synced_properties.id` |
| `wifi` | `Boolean` |
| `tv` | `Boolean` |
| `cooktop` | `Boolean` |
| `oven` | `Boolean` |
| `kettle` | `Boolean` |
| `dishwasher` | `Boolean` |
| `refrigerator` | `Boolean` |
| `microwave` | `Boolean` |
| `washer` | `Boolean` |
| `free_parking` | `Boolean` |
| `air_conditioning` | `Boolean` |
| `smoke_alarm` | `Boolean` |
| `fire_extinguisher` | `Boolean` |
| `synced_at` | `DateTime` |

---

#### `SyncedAllowedTenant` → `synced_allowed_tenants`

Read-only copy from MSSQL `AllowedTenants` table.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `property_id` | `Integer FK → synced_properties.id` | |
| `room_id` | `Integer FK → synced_rooms.id` | |
| `allows_families` | `Boolean` | |
| `allows_children` | `Boolean` | |
| `allows_students` | `Boolean` | |
| `student_gender` | `Integer` | `0` = male, `1` = female, `-1` = any |
| `allows_workers` | `Boolean` | |
| `worker_gender` | `Integer` | `0` = male, `1` = female, `-1` = any |
| `pets_allowed` | `Boolean` | |
| `synced_at` | `DateTime` | |

---

#### `UserProfile` → `user_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID PK` | Internal ID |
| `auth_user_id` | `UUID` | Auth system ID |
| `external_user_id` | `String(255) UNIQUE` | MSSQL user ID (the `user_id` used in API calls) |
| `full_name` | `Text` | |
| `phone` | `String(50)` | |
| `gender` | `String(20)` | |
| `birth_year` | `Integer` | |
| `nationality` | `String(100)` | |
| `occupation` | `String(100)` | |
| `college` | `String(200)` | Migration 008 |
| `sleep_schedule` | `String(50)` | Migration 008 |
| `smoking_status` | `String(30)` | Migration 008 |
| `visitor_frequency` | `String(30)` | Migration 008 |
| `created_at` | `DateTime` | |
| `updated_at` | `DateTime` | |

---

#### `QuestionnaireCategory` → `questionnaire_categories`

| Column | Type |
|--------|------|
| `id` | `Integer PK` |
| `name_ar` | `Text NOT NULL` |
| `name_en` | `Text NOT NULL` |
| `sort_order` | `Integer` |

---

#### `QuestionnaireQuestion` → `questionnaire_questions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `category_id` | `Integer FK → questionnaire_categories.id` | |
| `question_ar` | `Text NOT NULL` | Arabic text |
| `question_en` | `Text NOT NULL` | English text |
| `question_type` | `String(30) NOT NULL` | e.g., `choice`, `scale`, `text` |
| `options_ar` | `JSONB` | Arabic options array |
| `options_en` | `JSONB` | English options array |
| `weight` | `Float` | Importance weight for scoring |
| `sort_order` | `Integer` | Display order |
| `is_active` | `Boolean` | Soft enable/disable |

---

#### `UserQuestionnaireAnswer` → `user_questionnaire_answers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `user_id` | `String(255) NOT NULL` | External user ID |
| `question_id` | `Integer FK → questionnaire_questions.id NOT NULL` | |
| `answer_value` | `Text NOT NULL` | |
| `answer_scale` | `Integer` | Numeric scale value (1–5) |
| `answered_at` | `DateTime` | |
| **UniqueConstraint** | `(user_id, question_id)` | One answer per question per user |

---

#### `UserSearchPreference` → `user_search_preferences`

| Column | Type |
|--------|------|
| `id` | `Integer PK` |
| `user_id` | `String(255) UNIQUE NOT NULL` |
| `min_budget` | `Integer` |
| `max_budget` | `Integer` |
| `preferred_city` | `Text` |
| `preferred_government` | `Text` |
| `preferred_property_type` | `String(20)` |
| `furnished` | `Boolean` |
| `wifi` | `Boolean` |
| `air_conditioning` | `Boolean` |
| `balcony` | `Boolean` |
| `private_bathroom` | `Boolean` |
| `tenant_type` | `String(20)` |
| `gender_preference` | `String(20)` |
| `shared_room` | `Boolean` |
| `created_at` | `DateTime` |
| `updated_at` | `DateTime` |

---

#### `ScoringWeight` → `scoring_weights`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `weight_key` | `String(50) NOT NULL` | e.g., `"budget"`, `"location"` |
| `weight_value` | `Float NOT NULL` | e.g., `0.30` |
| `weight_group` | `String(30) NOT NULL` | `"property"`, `"room"`, `"matching"` |
| `description` | `Text` | |
| `updated_at` | `DateTime` | |
| **UniqueConstraint** | `(weight_key, weight_group)` | |

---

#### `UserFeedbackWeight` → `user_feedback_weights`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `user_id` | `String(255) NOT NULL` | |
| `city` | `Text` | Inferred preferred city |
| `government` | `Text` | Inferred preferred gov |
| `property_type` | `Integer` | Inferred preferred type |
| `min_budget` | `Float` | Inferred min budget |
| `max_budget` | `Float` | Inferred max budget |
| `boost_factor` | `Float` | Default `1.0` |
| `updated_at` | `DateTime` | |

---

#### `PropertyRecommendation` → `property_recommendations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `user_id` | `String(255) NOT NULL` | |
| `property_id` | `Integer FK → synced_properties.id NOT NULL` | |
| `score` | `Float NOT NULL` | Final weighted score |
| `score_breakdown` | `JSONB` | Per-factor scores dict |
| `rank` | `Integer` | |
| `created_at` | `DateTime` | |
| `expires_at` | `DateTime` | 24-hour TTL |
| **UniqueConstraint** | `(user_id, property_id)` | |

---

#### `RoomRecommendation` → `room_recommendations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `user_id` | `String(255) NOT NULL` | |
| `room_id` | `Integer FK → synced_rooms.id NOT NULL` | |
| `score` | `Float NOT NULL` | |
| `score_breakdown` | `JSONB` | |
| `rank` | `Integer` | |
| `created_at` | `DateTime` | |
| `expires_at` | `DateTime` | 24-hour TTL |
| **UniqueConstraint** | `(user_id, room_id)` | |

---

#### `RoommateMatch` → `roommate_matches`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `seeker_user_id` | `String(255) NOT NULL` | The user seeking roommates |
| `room_id` | `Integer FK → synced_rooms.id NOT NULL` | |
| `property_id` | `Integer FK → synced_properties.id NOT NULL` | |
| `room_compatibility_score` | `Float NOT NULL` | **Only this field is exposed via API** |
| `match_breakdown` | `JSONB` | **INTERNAL ONLY — NEVER returned via API** |
| `current_roommates` | `JSONB` | Info about existing roommates |
| `seeker_questionnaire_match` | `Float` | |
| `created_at` | `DateTime` | |
| `expires_at` | `DateTime` | 24-hour TTL |
| **UniqueConstraint** | `(seeker_user_id, room_id)` | |

---

#### `UserInteraction` → `user_interactions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer PK` | |
| `user_id` | `String(255) NOT NULL` | |
| `target_type` | `String(20) NOT NULL` | `"property"` or `"room"` |
| `target_id` | `Integer NOT NULL` | |
| `action` | `String(30) NOT NULL` | `viewed`, `saved`, `liked`, `skipped`, `contacted` |
| `context` | `JSONB` | Arbitrary context data |
| `dwell_seconds` | `Integer` | Time spent viewing (migration 008) |
| `search_lat` | `DOUBLE_PRECISION` | User's search location lat (migration 008) |
| `search_lng` | `DOUBLE_PRECISION` | User's search location lng (migration 008) |
| `created_at` | `DateTime` | |

---

#### `PropertyEmbedding` → `property_embeddings`

| Column | Type | Notes |
|--------|------|-------|
| `property_id` | `Integer PK, FK → synced_properties.id` | |
| `embedding` | `JSONB` | Migrated to `vector(384)` via pgvector |
| `updated_at` | `DateTime` | |

---

#### `UserEmbedding` → `user_embeddings`

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | `String(255) PK` | |
| `embedding` | `JSONB` | Migrated to `vector(384)` via pgvector |
| `updated_at` | `DateTime` | |

---

### 6.3 Migrations

**Tool:** Alembic, configured via `alembic.ini` and `alembic/env.py`.

The environment file injects `DATABASE_URL` from the environment and auto-discovers all models via `Base.metadata`.

| Migration | Revision | Parent | Creates / Changes |
|-----------|----------|--------|-------------------|
| `001_create_synced_tables.py` | `001` | `None` | `synced_properties`, `synced_rooms`, `synced_amenities`, `synced_allowed_tenants` |
| `002_create_user_tables.py` | `002` | `001` | `user_profiles`, `questionnaire_categories`, `questionnaire_questions`, `user_questionnaire_answers`, `user_search_preferences` |
| `003_create_recommendation_tables.py` | `003` | `002` | `property_recommendations`, `room_recommendations` |
| `004_create_matching_tables.py` | `004` | `003` | `roommate_matches` |
| `005_create_interactions.py` | `005` | `004` | `user_interactions`, `property_embeddings` (JSONB), `user_embeddings` (JSONB) |
| `006_create_embeddings.py` | `006` | `005` | Enables `pgvector`, drops/recreates embeddings as `vector(384)` |
| `007_create_weights_and_feedback.py` | `007` | `006` | `scoring_weights` (seeds 20 weight rows), `user_feedback_weights` |
| `008_add_dwell_and_profile_fields.py` | `008` | `007` | Adds `dwell_seconds`, `search_lat`, `search_lng` to `user_interactions`; adds `college`, `sleep_schedule`, `smoking_status`, `visitor_frequency` to `user_profiles` |

---

## 7. API Endpoints

**Base:** `http://localhost:8000`

**Auth:** All endpoints require `X-API-Key` header (skipped if `API_KEY` env var is empty).

### 7.1 Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns `{"status": "healthy"|"degraded", "database": "connected"|"disconnected"}` |

### 7.2 Sync

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sync/refresh` | Full sync — properties, rooms, amenities, allowed_tenants, users, preferences |
| `POST` | `/sync/users` | Sync only users (`AspNetUsers`/`Users`) + preferences from MSSQL |
| `GET` | `/sync/status` | Returns `{"status": "ok", "message": "Sync status endpoint"}` |

### 7.3 Recommendations

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| `GET` | `/recommend/properties/{user_id}` | `?city=&min_budget=&max_budget=&property_type=full\|shared&limit=` | Returns scored properties. Cold-start (no profile/prefs) → popularity-based. |
| `GET` | `/recommend/rooms/{user_id}` | `?city=&limit=` | Returns scored rooms with 8-factor breakdown |
| `POST` | `/recommend/compute/{user_id}` | — | Background recomputation of both property + room recommendations |

### 7.4 Matching

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/match/compute/{user_id}` | Computes pairwise compatibility for all rooms. Returns `room_compatibility_score` only (no `match_breakdown`). |
| `GET` | `/match/results/{user_id}` | Returns stored match results with `room_compatibility_score` |

### 7.5 Users

| Method | Path | Request Body | Description |
|--------|------|-------------|-------------|
| `POST` | `/users/profile` | `UserProfileCreate` | Create or update user profile |
| `GET` | `/users/profile/{user_id}` | — | Get user profile |
| `POST` | `/users/preferences` | `SearchPreferenceCreate` | Save search preferences |
| `GET` | `/users/preferences/{user_id}` | — | Get saved search preferences |

### 7.6 Questionnaire

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/questionnaire/questions` | List all questions grouped by category (Arabic + English) |
| `POST` | `/questionnaire/answers/{user_id}` | Submit answers (triggers background recomputation of recommendations) |
| `GET` | `/questionnaire/answers/{user_id}` | Get user's submitted answers |

### 7.7 Interactions

| Method | Path | Request Body | Description |
|--------|------|-------------|-------------|
| `POST` | `/interactions` | `InteractionCreate` | Log interaction (viewed/saved/liked/skipped/contacted) |
| `GET` | `/interactions/{user_id}` | — | Get user's interaction history |

### 7.8 Analysis

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze/{user_id}` | Analyze interactions → infer preferences (requires 3+ interactions) |
| `GET` | `/classify/{user_id}` | Classify user into behavioral segments |
| `GET` | `/heatmap/{user_id}` | Get location heatmap clusters |
| `POST` | `/interactions/feedback/{user_id}` | Learn from interactions (compute boost/penalty and store in feedback weights) |

### 7.9 Admin / A/B Testing

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/weights` | List all scoring weights across all groups |
| `GET` | `/admin/weights/{group}` | Get weights for a group (`property` / `room` / `matching`) |
| `PUT` | `/admin/weights/{group}/{key}?value=X.XX` | Update a specific weight |
| `POST` | `/admin/sync-preferences` | Trigger chatbot preferences bridge sync |

---

## 8. Schemas (Pydantic)

**File:** `app/schemas/recommendation.py`

### `UserProfileCreate`
```python
class UserProfileCreate(BaseModel):
    user_id: str                    # Required
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    college: Optional[str] = None
    sleep_schedule: Optional[str] = None
    smoking_status: Optional[str] = None
    visitor_frequency: Optional[str] = None
```

### `SearchPreferenceCreate`
```python
class SearchPreferenceCreate(BaseModel):
    user_id: str                    # Required
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    preferred_city: Optional[str] = None
    preferred_government: Optional[str] = None
    preferred_property_type: Optional[str] = None
    furnished: Optional[bool] = None
    wifi: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    balcony: Optional[bool] = None
    private_bathroom: Optional[bool] = None
    tenant_type: Optional[str] = None
    gender_preference: Optional[str] = None
    shared_room: Optional[bool] = None
```

### `AnswerSubmit`
```python
class AnswerSubmit(BaseModel):
    question_id: int
    answer_value: str
    answer_scale: Optional[int] = None
```

### `QuestionnaireAnswersSubmit`
```python
class QuestionnaireAnswersSubmit(BaseModel):
    answers: list[AnswerSubmit]
```

### `InteractionCreate`
```python
class InteractionCreate(BaseModel):
    user_id: str                    # Required
    target_type: str                # Required ("property" | "room")
    target_id: int                  # Required
    action: str                     # Required ("viewed" | "saved" | "liked" | "skipped" | "contacted")
    context: Optional[dict] = None
    dwell_seconds: Optional[int] = None
    search_lat: Optional[float] = None
    search_lng: Optional[float] = None
```

---

## 9. Scoring Pipeline

### 9.1 BaseScorer

**File:** `app/services/scoring/base_scorer.py`

```python
class BaseScorer(ABC):
    @abstractmethod
    def score(self, user, candidate, context=None) -> float:
        """Return a score between 0.0 and 1.0."""
        pass
```

All concrete scorers extend this.

### 9.2 BudgetScorer

**File:** `app/services/scoring/budget_scorer.py`

Evaluates how well the candidate's rent fits the user's budget.

| Condition | Score |
|-----------|-------|
| Rent is within budget range (`min_budget` ≤ rent ≤ `max_budget`) | `1.0` |
| Rent is below min budget | Proportional: `rent / min_budget` |
| Rent is up to 20% over max budget | `0.7` |
| Rent is more than 20% over max budget | Linear decay: `1.0 - (rent - max) / max` (min `0.0`) |
| No budget set on user or candidate | `0.5` |
| No rent on candidate | `0.0` |

- Reads `monthly_rent` from properties, `month_rent` from rooms.
- Budget comes from user object (`max_budget`/`min_budget`) or `context`.

### 9.3 LocationScorer

**File:** `app/services/scoring/location_scorer.py`

Evaluates geographic proximity to user's preferred location.

| Condition | Score |
|-----------|-------|
| Exact city match | `1.0` |
| Exact governorate match | `1.0` |
| Different governorate | Geographic distance decay via `geo_distance()`: `max(0.0, 1.0 - dist_km / 200)` |
| No preference set | `0.5` |

- Uses Haversine formula for distance calculation.
- Governates include all 27 Egyptian governorates.

### 9.4 AmenityScorer

**File:** `app/services/scoring/amenity_scorer.py`

Evaluates how well the property's amenities match the user's desired amenities.

**Tracked amenity fields:** `wifi`, `air_conditioning`, `balcony`, `private_bathroom`

| Condition | Score |
|-----------|-------|
| User wants amenities | Ratio of matched amenities to wanted amenities |
| No preferences set | `0.5` |
| `furnished` preference checked and property is furnished | Counted as an amenity match |
| Property has no amenities record | `0.3` |

### 9.5 TenantScorer

**File:** `app/services/scoring/tenant_scorer.py`

Evaluates whether the user's profile is allowed by the property/room's tenant restrictions.

**Constants:** `MATCH = 1.0`, `BLOCKED = 0.0`, `FLEXIBLE = 0.8`

| Condition | Score |
|-----------|-------|
| Gender matches exactly (student_gender/worker_gender matches user gender) | `1.0` |
| Gender mismatch with strict restriction | `0.0` |
| Occupation match (student/worker) | `1.0` |
| Occupation mismatch with restriction | `0.0` |
| Property allows families/children | `1.0` |
| No tenant restrictions | `0.5` |

### 9.6 QuestionnaireScorer

**File:** `app/services/scoring/questionnaire_scorer.py`

Evaluates consistency between questionnaire answers and the property type.

- Checks question IDs `1` and `2` for preferred property type.
- Maps preferred type to `property_type` (`0` = full, `1` = shared).

| Condition | Score |
|-----------|-------|
| Questionnaire answer matches property type | `1.0` |
| Mismatch | `0.3` |
| No answers | Factor omitted |

### 9.7 FeedbackScorer

**File:** `app/services/scoring/feedback_scorer.py`

Learns from user interactions to boost or penalize properties/rooms.

**Boost constants:**
- `BOOST_SAVE = 1.3`
- `BOOST_LIKE = 1.2`
- `BOOST_VIEW = 1.05`
- `PENALTY_SKIP = 0.7`

**Methods:**

| Method | Description |
|--------|-------------|
| `compute_boost(user_id, property_id)` | Returns the boost factor from `user_feedback_weights` table |
| `learn_from_interaction(user_id, interactions, properties)` | Requires 3+ interactions in 24h, 2+ saved/liked. Analyzes trends in city, government, type, budget. Upserts boost factor to `user_feedback_weights`. |

---

## 10. Ranking & Weights

### 10.1 Ranker

**File:** `app/services/ranking/ranker.py`

```python
class Ranker:
    def __init__(self, weights: dict, group: str = None):
        self.weights = weights
        self.group = group

    def _load_weights(self) -> dict:
        # If group is set, loads from DB `scoring_weights` table, overriding defaults

    def weighted_sum(self, score_breakdown: dict) -> float:
        # Computes: sum(weight * score) / sum(weight) for all keys
        # Unknown keys get 0 weight
```

- If `group` is provided, weights are loaded from the `scoring_weights` table (allowing runtime tuning).
- If a weight key in the breakdown doesn't exist in `self.weights`, it's assigned weight `0`.

### 10.2 Default Weights

**File:** `app/utils/weights.py`

#### Property Score Weights

```python
PROPERTY_WEIGHTS = {
    "budget": 0.30,
    "location": 0.25,
    "amenities": 0.15,
    "tenant": 0.10,
    "furnished": 0.05,
    "property_type": 0.10,
    "recency": 0.00,       # Future use
    "questionnaire": 0.05,
}
```

**Total:** 1.00

#### Room Score Weights

```python
ROOM_WEIGHTS = {
    "budget": 0.25,
    "location": 0.20,
    "capacity": 0.15,
    "amenities": 0.10,
    "tenant": 0.10,
    "furnished": 0.05,
    "room_type": 0.10,
    "recency": 0.05,
}
```

**Total:** 1.00

#### Matching Weights

```python
MATCHING_WEIGHTS = {
    "questionnaire": 0.50,
    "gender": 0.15,
    "occupation": 0.10,
    "age_group": 0.10,
    "lifestyle": 0.15,
}
```

**Total:** 1.00

---

## 11. Recommenders

### 11.1 PropertyRecommender

**File:** `app/services/recommendation/property_recommender.py`

**Pipeline:**

1. **`_check_cache()`** — 1-hour TTL in-memory check. Queries `property_recommendations` for non-expired entries. Returns cached results if found.

2. **`_prefilter(properties, context)`** — Filters by city (if specified) and budget (1.5x max budget tolerance).

3. **Per-candidate scoring (7 factors):**
   - `budget` → `BudgetScorer.score()`
   - `location` → `LocationScorer.score()`
   - `amenities` → `AmenityScorer.score()`
   - `tenant` → `TenantScorer.score()`
   - `furnished` → `1.0` if furnished matches preference, else `0.5`
   - `property_type` → `1.0` if type matches preference, else `0.5`
   - `questionnaire` → `QuestionnaireScorer.score()`

4. **`_session_boost()`** — Boosts candidates recently viewed by the user.

5. **`_apply_diversity()`** — Caps at **max 3 properties per city**.

6. **Sort** by score descending → update cache.

### 11.2 RoomRecommender

**File:** `app/services/recommendation/property_recommender.py`

**Pipeline:**

1. **`_check_cache()`** — Same 1-hour TTL pattern.

2. **Per-room scoring (8 factors):**
   - `budget` → `BudgetScorer.score()`
   - `location` → `LocationScorer.score()`
   - `capacity` → Ratio of available to total capacity
   - `amenities` → `AmenityScorer.score()`
   - `tenant` → `TenantScorer.score()`
   - `furnished` → `1.0` if furnished, `0.5` otherwise
   - `room_type` → `1.0` if ensuite bathroom, `0.8` if shared bathroom
   - `recency` → Higher for recently available rooms

3. **`_session_boost()`** — Same as property.

4. **`_apply_diversity()`** — Caps at **max 2 rooms per property**.

5. **Sort** by score descending → update cache.

---

## 12. Compatibility Engine (Matching)

**File:** `app/services/matching/compatibility_engine.py`

### `CompatibilityEngine`

#### `compute_for_user(seeker_id) → dict`

1. Load seeker's questionnaire answers + profile from DB
2. Find all non-deleted rooms with `capacity_available > 0`
3. For each room:
   a. Find all **other users** who have answers for the same questions
   b. Compute pairwise compatibility scores between seeker and each roommate candidate
   c. Filter: keep only pairs with score ≥ `0.3`
   d. Aggregate: `room_score = avg(pairwise_scores) * (0.7 + 0.3 * capacity_factor)`
4. Save results to `roommate_matches` table:
   - `room_compatibility_score` ← the aggregated room score (**exposed via API**)
   - `match_breakdown` ← detailed per-roommate breakdown (**NEVER exposed via API — internal only**)
5. Return results with only `room_compatibility_score` visible

#### `_compute_pairwise(answers_a, answers_b, profile_a, profile_b) → float`

| Factor | Calculation | Weight |
|--------|-------------|--------|
| **Questionnaire similarity** | Scale-based: `1 - abs(diff / 4)`; Exact match: `1.0` if same, `0.0` if not | 0.50 |
| **Lifestyle similarity** | Subset of question IDs {4, 5, 6, 7, 8} (sleep, smoking, visitors, noise, exercise) | 0.15 |
| **Gender similarity** | Same gender → `1.0`, Different → `0.3` | 0.15 |
| **Occupation similarity** | Same occupation → `1.0`, Different → `0.4` | 0.10 |
| **Age similarity** | `max(0, 1 - age_diff / 20)` | 0.10 |

---

## 13. Data Sync Service

**File:** `app/services/sync/data_sync.py`

### `DataSyncService`

| Method | MSSQL Source Table | PostgreSQL Target | Notes |
|--------|-------------------|-------------------|-------|
| `sync_all(since=None)` | All | All | Orchestrates all sync methods |
| `sync_properties()` | `Properties WHERE IsDeleted = 0` | `synced_properties` | Batch size 500 |
| `sync_rooms()` | `Rooms WHERE IsDeleted = 0` | `synced_rooms` | Batch size 500 |
| `sync_amenities()` | `PropertyAmenities` | `synced_amenities` | Batch size 500 |
| `sync_allowed_tenants()` | `AllowedTenants WHERE IsDeleted = 0` | `synced_allowed_tenants` | Batch size 500 |
| `sync_users()` | `AspNetUsers` or `Users` (auto-detected) | `user_profiles` | Reads safe columns only. Upsert by `external_user_id`. |
| `sync_user_preferences()` | `UserPreferences` / `UserProfiles` / `SearchPreferences` (auto-detected) | `user_search_preferences` | Requires `UserId`, `MinBudget`, `MaxBudget`, `PreferredCity` |

All operations use `INSERT ... ON CONFLICT DO UPDATE` for idempotent upserts.

---

## 14. Interaction Analyzer & Classification

**File:** `app/services/interaction_analyzer.py`

### `InteractionAnalyzer`

**Constant:** `MIN_INTERACTIONS_FOR_ANALYSIS = 3`

**`analyze(user_id) → dict`:**
1. Load all interactions for user
2. Require at least 3 interactions, at least 1 of type `"property"`
3. Read property details from MSSQL (via `mssql_reader.get_properties_batch`)
4. Extract weighted preferences based on interaction weights
5. Upsert inferred preferences into `user_search_preferences`
6. Return analysis summary

**Interaction Weights:**
```python
INTERACTION_WEIGHTS = {
    "dwell_high": 3.0,
    "saved": 2.5,
    "liked": 2.0,
    "contacted": 2.0,
    "dwell_medium": 1.5,
    "viewed": 1.0,
    "skipped": 0.3,
}
```

### `UserClassifier`

**`classify(user_id, preferences) → dict`**

Segments users into behavioral categories:

| Segment | Criteria |
|---------|----------|
| `careful_evaluator` | High dwell time, high save rate |
| `decisive_buyer` | Low dwell time, high save rate |
| `explorer_browser` | High dwell time, low save rate |
| `balanced_browser` | Medium dwell time, medium save rate |
| `high_interest_user` | Many interactions overall |
| `budget_conscious` | Stays within strict budget range |
| `privacy_seeker` | Prefers full apartments, private bathroom |
| `premium_segment` | High budget, prefers furnished |

### `get_similar_properties(property_id, limit=5) → list`

Collaborative filtering via co-occurrence — finds properties that users who viewed `property_id` also viewed.

---

## 15. Location Heatmap

**File:** `app/services/location_heatmap.py`

### `LocationHeatmap`

**`analyze(user_id) → dict`:**
1. Load all interaction records with `search_lat`/`search_lng` values
2. Require at least 2 location-tagged interactions
3. Cluster points using **1500m Haversine radius** (dbscan-like approach)
4. Return top **5 clusters** with center `(lat, lng)` and interaction count

---

## 16. Preferences Bridge

**File:** `app/services/preferences_bridge.py`

### `PreferencesBridge`

**`sync_all() → dict`:**
- Reads from `user_preferences` table (created by the chatbot system)
- Upserts into `user_search_preferences` (used by the recommendation engine)
- Maps: `UserId → user_id`, `MinBudget → min_budget`, `MaxBudget → max_budget`, `PreferredCity → preferred_city`
- Runs automatically on application **startup** (via `lifespan`)

---

## 17. Questionnaire Content

Seeded by `scripts/seed_questionnaire.py`. 16 questions across 4 categories:

### Category 1: Personality & Career (3 questions)

| ID | English Question | Type | Options |
|----|-----------------|------|---------|
| 1 | What best describes your current status? | choice | Student, Employee, Freelancer, Entrepreneur, Job Seeker |
| 2 | What is your college/major? | choice | Engineering, Medicine, Pharmacy, Science, Literature, Business, Law, Other |
| 3 | How would you describe your personality? | choice | Organized, Social, Quiet, Flexible, Easy-going |

### Category 2: Lifestyle & Habits (5 questions)

| ID | English Question | Type | Options |
|----|-----------------|------|---------|
| 4 | What is your sleep schedule like? | choice | Early bird, Moderate, Late, Night owl |
| 5 | Do you smoke? | choice | Never, Cigarettes, Shisha, Vape, Occasionally |
| 6 | How often do you have visitors? | choice | Rarely, Sometimes, Often, Always |
| 7 | What noise level do you prefer? | scale | 1 (Very quiet) – 5 (Lively) |
| 8 | How often do you exercise? | scale | 1 (Never) – 5 (Daily) |

### Category 3: Social & Cohabitation (4 questions)

| ID | English Question | Type | Options |
|----|-----------------|------|---------|
| 9 | How do you handle conflicts? | choice | Talk it out, Need space, Compromise, Avoid |
| 10 | How often do you want to interact with roommates? | scale | 1 (Minimal) – 5 (Very social) |
| 11 | Do you prefer sharing food/items? | choice | Yes, Sometimes, No |
| 12 | What's your stance on hosting friends? | choice | Allowed anytime, Allowed with notice, Rarely, Not allowed |

### Category 4: Finance & Cleanliness (4 questions)

| ID | English Question | Type | Options |
|----|-----------------|------|---------|
| 13 | How do you prefer to split bills? | choice | Equally, By usage, Rotating, Landlord inclusive |
| 14 | How do you handle rent/bill payments? | choice | Always on time, Occasionally late, Need reminders, Struggle sometimes |
| 15 | What cleanliness level do you prefer? | scale | 1 (Relaxed) – 5 (Very clean) |
| 16 | How do you prefer to divide chores? | choice | Equal rotation, By ability, Hire cleaning, Each does own |

---

## 18. Repositories

**Files:** `app/repositories/property_repo.py`, `app/repositories/weights_repo.py`

| Repository | Key Methods | Returns |
|------------|-------------|---------|
| `PropertyRepository` | `get_all_approved()`, `get_by_id()`, `get_by_city()`, `get_with_relations()` | SQLAlchemy model instances |
| `RoomRepository` | `get_available()`, `get_by_property()`, `get_by_id()` | Room model with eager-loaded relationships |
| `UserRepository` | `upsert_profile(user_id, data)`, `get_profile(user_id)` | UserProfile |
| `QuestionnaireRepository` | `get_categories()`, `get_questions()`, `save_answers()`, `get_answers()` | Categories with nested questions |
| `SearchPreferenceRepository` | `upsert(user_id, data)`, `get(user_id)` | UserSearchPreference |
| `RecommendationRepository` | `save_property_recommendations()`, `save_room_recommendations()`, `get_property_recommendations()`, `get_room_recommendations()` | Bulk save (delete old + insert new) |
| `MatchingRepository` | `save_match(data)`, `get_matches(user_id)` | RoommateMatch (upsert pattern) |
| `InteractionRepository` | `log(data)`, `get_by_user()`, `get_high_dwell()`, `get_location_clusters()`, `get_interaction_count()` | UserInteraction |
| `WeightRepository` | `get_weights(group)`, `update_weight()`, `get_all_weights()` | Dict of key→value, or list |
| `FeedbackRepository` | `get_user_feedback(user_id)`, `upsert_feedback(user_id, data)`, `delete_user_feedback(user_id)` | UserFeedbackWeight |

---

## 19. Utilities

### `app/utils/location.py`

| Function | Description |
|----------|-------------|
| `geo_distance(lat1, lon1, lat2, lon2)` | Haversine distance in km. Returns `inf` if any coordinate is `None`. |
| `governorate_center(name)` | Returns `(lat, lon)` tuple for a named Egyptian governorate. |
| `GOVERNORATE_CENTERS` | Dict of 27 Egyptian governorates with center coordinates. |

### `app/utils/weights.py`

| Constant | Description |
|----------|-------------|
| `PROPERTY_WEIGHTS` | 8-factor weight dict for property scoring (see §10.2) |
| `ROOM_WEIGHTS` | 8-factor weight dict for room scoring (see §10.2) |
| `MATCHING_WEIGHTS` | 5-factor weight dict for roommate matching (see §10.2) |

---

## 20. Testing

**All tests use mocks** — no real database or external services.

### Test Infrastructure

**File:** `tests/conftest.py`

| Fixture | Description |
|---------|-------------|
| `MockProperty` | Dict-like object with property fields |
| `MockRoom` | Dict-like object with room fields |
| `MockAllowedTenant` | Dict-like with tenant restriction fields |
| `MockAmenity` | Dict-like with amenity fields |
| `MockUser` | User with search preferences |
| `MockProfile` | User profile (gender, occupation, birth_year) |
| `MockInteraction` | Interaction record with action, dwell_seconds, etc. |
| `sample_properties` | List of 4 `MockProperty` fixtures |
| `sample_rooms` | List of 3 `MockRoom` fixtures |
| `sample_tenant_allowed` | Permissive tenant fixture |
| `sample_tenant_female` | Female-only tenant fixture |
| `sample_amenities` | Amenity fixture with wifi, AC, etc. |
| `male_user` | MockUser with gender="male" |
| `female_user` | MockUser with gender="female" |

### Test Coverage (83 tests across 10 files)

| File | Tests | What it covers |
|------|-------|----------------|
| `test_budget_scorer.py` | 11 | Perfect budget, below min, slightly over, way over, no budget, no rent, context override, etc. |
| `test_location_scorer.py` | 5 | City match, governorate match, no preference, different governorates, context |
| `test_amenity_scorer.py` | 5 | All match, partial match, no preferences, no amenities on property, furnished as amenity |
| `test_tenant_scorer.py` | 8 | Gender match, gender block, no restriction, families allowed, no tenants, occupation mismatch |
| `test_ranker.py` | 7 | Weighted sum calculations, perfect/zero/mixed/empty breakdowns, property ranking, room diversity, capacity scoring, ensuite premium |
| `test_matching.py` | 8 | Questionnaire similarity (same, different, no shared, scale, mixed, empty), pairwise computation, gender mismatch, room aggregation |
| `test_schemas.py` | 5 | Profile validation (valid, minimal, missing user_id), interaction validation, questionnaire answers |
| `test_feedback_scorer.py` | 3 | Default boost, custom boost, penalty |
| `test_interaction_analyzer.py` | 13 | Analyzer (not enough interactions, basic preferences, dwell weight), classifier (no interactions, high save, high dwell, premium), heatmap (haversine, same point, insufficient, clustering) |
| `test_utils.py` | 8 | Weights sum to 1.0, keys match, geo_distance calculations, governorate centers |

### Running Tests

```bash
PYTHONPATH=. python -m pytest tests/ -v            # All tests
PYTHONPATH=. python -m pytest tests/test_budget_scorer.py -v  # Single file
PYTHONPATH=. python -m pytest -k "test_name" -v     # Single test
```

---

## 21. Deployment

### Docker

**File:** `Dockerfile`
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y unixodbc unixodbc-dev freetds-dev freetds-bin
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Railway

**File:** `railway.toml`
```toml
[build]
  builder = "DOCKERFILE"
  dockerfile_path = "Dockerfile"
[service]
  port = 8000
```

**Startup sequence:**
1. Build Docker image from `Dockerfile`
2. Install ODBC driver + FreeTDS for MSSQL connectivity
3. Install Python dependencies
4. Run `alembic upgrade head` (applies all pending migrations)
5. Start `uvicorn` server on port 8000

**Application startup** (FastAPI `lifespan`):
1. Check database connection (`test_connection()`)
2. Run `PreferencesBridge.sync_all()` (sync chatbot preferences)

---

## 22. Common Commands

```bash
# Run all tests
PYTHONPATH=. python -m pytest tests/ -v

# Run a specific test file
PYTHONPATH=. python -m pytest tests/test_budget_scorer.py -v

# Start development server
# PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Run migrations
alembic upgrade head

# Seed questionnaire (first time only)
PYTHONPATH=. python scripts/seed_questionnaire.py

# Manual full MSSQL sync
PYTHONPATH=. python scripts/sync_data.py

# Trigger full sync via API
curl -X POST http://localhost:8000/sync/refresh \
  -H "X-API-Key: your-key"

# Sync only users from MSSQL
curl -X POST http://localhost:8000/sync/users \
  -H "X-API-Key: your-key"

# Create/update user profile
curl -X POST http://localhost:8000/users/profile \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"guid-...","full_name":"John","gender":"male"}'

# Get property recommendations
curl -X GET "http://localhost:8000/recommend/properties/user-123?city=Cairo&limit=10" \
  -H "X-API-Key: your-key"

# Get room recommendations
curl -X GET "http://localhost:8000/recommend/rooms/user-123?city=Cairo&limit=10" \
  -H "X-API-Key: your-key"

# Log an interaction
curl -X POST http://localhost:8000/interactions \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-123","target_type":"property","target_id":42,"action":"viewed","dwell_seconds":30}'

# Get all scoring weights
curl -X GET http://localhost:8000/admin/weights \
  -H "X-API-Key: your-key"

# Update a weight
curl -X PUT "http://localhost:8000/admin/weights/property/budget?value=0.35" \
  -H "X-API-Key: your-key"

# Compute recommendations (background)
curl -X POST http://localhost:8000/recommend/compute/user-123 \
  -H "X-API-Key: your-key"

# Compute roommate matches
curl -X POST http://localhost:8000/match/compute/user-123 \
  -H "X-API-Key: your-key"

# Get match results
curl -X GET http://localhost:8000/match/results/user-123 \
  -H "X-API-Key: your-key"
```

---

*Document generated 2026-06-10. This reference covers all models, endpoints, scorers, services, tests, and deployment configuration.*