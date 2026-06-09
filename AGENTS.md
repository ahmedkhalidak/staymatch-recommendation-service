# StayMatch Recommendation Service — Agent Guide

## Commands

```bash
# Run all tests (no real DB needed — all mocks)
PYTHONPATH=. python -m pytest tests/ -v

# Run a single test file
PYTHONPATH=. python -m pytest tests/test_budget_scorer.py -v

# Start dev server
uvicorn app.main:app --reload --port 8000

# Run migrations
alembic upgrade head

# Seed questionnaire (first time only)
python scripts/seed_questionnaire.py

# Manual MSSQL sync
python scripts/sync_data.py

# Trigger full sync via API (properties + rooms + users)
curl -X POST http://localhost:8000/sync/refresh -H "X-API-Key: your-key"

# Sync only users from MSSQL
curl -X POST http://localhost:8000/sync/users -H "X-API-Key: your-key"

# Create/update a user profile
curl -X POST http://localhost:8000/users/profile \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"guid-...","full_name":"John","gender":"male"}'
```

`PYTHONPATH=.` is required before `pytest` (`python -m pytest` to avoid import issues) and any `python scripts/` invocation.

## Architecture

- **Single package** (`app/`), not a monorepo. FastAPI 0.104 + SQLAlchemy 2.0 + PostgreSQL (Neon).
- **Entrypoint:** `app/main.py` — creates FastAPI app, includes `health_router` and `main_router`.
- **Config:** `app/config.py` uses `pydantic-settings`, reads from `.env`. Settings are loaded on-the-fly (no shared singleton).
- **All endpoints** require `X-API-Key` header (checked by `app/core/security.py:verify_api_key`). Set `API_KEY` env var; if empty, auth is skipped.
- **Two databases:** PostgreSQL (Neon) for our data, MSSQL for sync (FreeTDS/ODBC 17 via `pyodbc`). MSSQL engine created in `app/database/session.py:get_mssql_engine()`. All sync is read-only from MSSQL — never writes to it.

## API Endpoints

- **`GET /recommend/properties/{user_id}`** supports filter query params: `?city=&min_budget=&max_budget=&property_type=full|shared&limit=`. These filter the already-scored (potentially cached) results without recomputation.
- **`GET /recommend/rooms/{user_id}`** supports `?city=&limit=`.
- **`POST /sync/users`** triggers MSSQL user sync — reads `AspNetUsers`/`Users` table (read-only), maps to `user_profiles` in PostgreSQL. Also syncs `UserPreferences` if the table exists.

## Scoring Pipeline

- **Per-property/room scorers** in `app/services/scoring/` (budget, location, amenity, tenant, questionnaire). All extend `BaseScorer`.
- **Ranker** (`app/services/ranking/ranker.py`) computes `weighted_sum()` from hardcoded weights in `app/utils/weights.py`.
- **Recommenders** (`app/services/recommendation/property_recommender.py`) orchestrate: prefilter → score each factor → rank → diversity (max 3 per city for properties, max 2 per building for rooms).
- **Caching:** recommendations cached 1 hour in-memory (`_check_cache`), stored in DB with 24h TTL. Cleared & rewritten on recompute.
- **Roommate matching** (`app/services/matching/compatibility_engine.py`): pairwise questionnaire similarity, aggregates per-room. `match_breakdown` stored but NEVER returned via API — only `room_compatibility_score` is exposed.
- **Feedback scorer** (`app/services/scoring/feedback_scorer.py`): learns from interactions to boost/penalize.

## Testing

- **All tests use mocks** — no real database or external service. Fixtures in `tests/conftest.py` define `MockProperty`, `MockRoom`, `MockUser`, etc.
- Test files correspond to scorers + ranker + schemas + matching + interaction analyzer. No integration or e2e tests.
- No linter/formatter config found — no conventions to enforce.

## DB & Migrations

- 20 tables across 8 migration files in `alembic/versions/`.
- **Synced tables** (read-only copies from MSSQL): `synced_properties`, `synced_rooms`, `synced_amenities`, `synced_allowed_tenants`.
- **Owned tables:** `user_profiles`, `user_search_preferences`, `questionnaire_categories/questions`, `user_questionnaire_answers`, `property_recommendations`, `room_recommendations`, `roommate_matches`, `user_interactions`, `scoring_weights`, `user_feedback_weights`, `property_embeddings`, `user_embeddings`.
- Alembic `env.py` injects `DATABASE_URL` from environment, discovers models via `Base.metadata`.

## Data Flow

- **Startup:** `lifespan` in `main.py` checks DB connection and runs `PreferencesBridge.sync_all()` (copies chatbot's `user_preferences` → `user_search_preferences`).
- **Recommendations** computed on GET or via `POST /recommend/compute/{user_id}` (background task).
- **Questionnaire answers** trigger background recomputation of both property and room recommendations.
- **Interactions** logged via `POST /interactions`. Analyzer (`app/services/interaction_analyzer.py`) infers preferences from dwell time, saves, likes.
- **Weight updates** take effect immediately (next recommendation) — no deploy needed.
- **User sync** reads from MSSQL `AspNetUsers`/`Users` table (read-only) and upserts into our `user_profiles` table. Also syncs `UserPreferences` if it exists. All sync is read-only from MSSQL — never writes to it.

## Deployment

- **Railway (Docker).** `Dockerfile` runs: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **`docs/` is empty** — no prose documentation beyond README.