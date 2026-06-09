# StayMatch Recommendation Service




## 📋 What This Service Does

This is a **standalone AI-powered recommendation and roommate matching engine** that:

1. **Recommends Properties** — Scores every property against a user's preferences (budget, location, amenities, tenant type)
2. **Recommends Rooms** — Scores individual rooms with diversity rules (max 2 results per building)
3. **Matches Roommates** — Computes pairwise compatibility between users using questionnaire answers + demographics
4. **Learns from Interactions** — Tracks dwell time, saves, views, and infers preferences automatically
5. **Tracks Location Heatmaps** — Clusters search coordinates to identify preferred neighborhoods
6. **Supports A/B Testing** — All scoring weights are stored in DB and adjustable via API

### Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────────────┐
│  React    │ ──▶ │ ASP.NET API  │ ──▶ │ Recommendation API   │
│  Frontend │     │ (your team)  │     │ (FastAPI + AI)       │
└──────────┘     └──────┬───────┘     └──────────┬───────────┘
                        │                        │
                        ▼                        ▼
                 ┌──────────────┐        ┌───────────────────┐
                 │   MSSQL DB   │        │ PostgreSQL (Neon) │
                 │ (ASP.NET)    │ sync   │ (our engine)      │
                 └──────────────┘        └───────────────────┘
```

**Key rule:** This service OWNS all its data. ASP.NET consumes our APIs — we don't depend on ASP.NET's data except the sync from MSSQL.

---

## 🧠 Scoring System

### Property Recommendation Score

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Budget | 30% | How well monthly_rent fits user's budget |
| Location | 25% | City/governorate match, geo-distance fallback |
| Amenities | 15% | Wifi, AC, balcony, washer matching |
| Tenant | 10% | Gender strict filtering + occupation match |
| Property Type | 10% | Full apartment vs shared housing preference |
| Furnished | 5% | Furnished status match |
| Recency | 5% | Newly added properties get a boost |

### Room Recommendation Score

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Budget | 25% | Room-level price fit |
| Location | 20% | Property city/gov match |
| Capacity | 15% | Available capacity score |
| Amenities | 10% | Property amenities match |
| Tenant | 10% | Gender + occupation compatibility |
| Furnished | 5% | Room furnished status |
| Room Type | 10% | Ensuite vs shared bathroom premium |
| Recency | 5% | Newly added rooms boost |

### Roommate Matching Score (SECRET)

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Questionnaire | 50% | Answer similarity (scale diff/4, choice match/miss) |
| Gender | 15% | Same gender preference |
| Occupation | 10% | Student↔student, worker↔worker |
| Age Group | 10% | Close age similarity |
| Lifestyle | 15% | Lifestyle question overlap |

> **⚠️ Secrecy rule:** Individual pairwise scores are stored internally in `roommate_matches.match_breakdown`. The API NEVER exposes individual scores — only the aggregated `room_compatibility_score`.

---

## 📡 API Reference — For ASP.NET Backend Team

All endpoints require `X-API-Key` header.

### Health

```
GET /health
Response: { "status": "healthy", "database": "connected" }
```

### Sync (MSSQL → PostgreSQL)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sync/refresh` | Trigger full data sync from MSSQL |
| `GET` | `/sync/status` | Get last sync timestamps |

**Call this after any property CRUD in ASP.NET.**

### Recommendations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recommend/properties/{user_id}` | Get property recommendations for user |
| `GET` | `/recommend/rooms/{user_id}` | Get room recommendations for user |
| `POST` | `/recommend/compute/{user_id}` | Recompute + cache recommendations |

**Response format:**
```json
{
  "user_id": "user_123",
  "recommendations": [
    {
      "property_id": 42,
      "score": 0.87,
      "score_breakdown": {
        "budget": 1.0, "location": 1.0, "amenities": 0.67,
        "tenant": 1.0, "furnished": 1.0, "property_type": 1.0, "recency": 0.5
      },
      "rank": 0
    }
  ]
}
```

### Roommate Matching

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/match/compute/{user_id}` | Compute pairwise compatibility for all rooms |
| `GET` | `/match/results/{user_id}` | Get stored compatibility scores (aggregated only) |

**Match compute response:**
```json
{
  "status": "completed",
  "seeker_user_id": "user_123",
  "matches_count": 5,
  "matches": [
    {
      "room_id": 15, "property_id": 7,
      "room_compatibility_score": 0.85,
      "roommate_count": 2
    }
  ]
}
```

### User Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users/profile` | Create or update user profile |
| `GET` | `/users/profile/{user_id}` | Get profile |
| `POST` | `/users/preferences` | Save search preferences |
| `GET` | `/users/preferences/{user_id}` | Get search preferences |

**Profile fields:** `user_id`, `full_name`, `gender`, `birth_year`, `occupation`, `college`, `sleep_schedule`

### Questionnaire

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/questionnaire/questions` | List all questions with categories |
| `POST` | `/questionnaire/answers/{user_id}` | Submit answers (triggers recomputation) |
| `GET` | `/questionnaire/answers/{user_id}` | Get user's answers |

**Questions are 16, across 4 categories:**
1. Personality & Career (3 questions)
2. Lifestyle & Habits (5 questions)
3. Social & Cohabitation (4 questions)
4. Finance & Cleanliness (4 questions)

### Interactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/interactions` | Log interaction (viewed/saved/liked/skipped) |
| `GET` | `/interactions/{user_id}` | Get user's lifetime interactions |

**Interaction payload:**
```json
{
  "user_id": "user_123",
  "target_type": "property",
  "target_id": 42,
  "action": "viewed",
  "dwell_seconds": 35,
  "search_lat": 30.0444,
  "search_lng": 31.2357
}
```

### Smart Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze/{user_id}` | Analyze interactions → infer preferences |
| `GET` | `/classify/{user_id}` | Classify user into behavioral segments |
| `GET` | `/heatmap/{user_id}` | Get location heatmap (search clusters by lat/lng) |
| `POST` | `/interactions/feedback/{user_id}` | Learn from interactions (boost/penalty) |

### A/B Testing Weights

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/weights` | List all scoring weights |
| `GET` | `/admin/weights/{group}` | Get weights for a group (property/room/matching) |
| `PUT` | `/admin/weights/{group}/{key}?value=0.XX` | Update a weight |

**Weight groups:** `property` (7 weights), `room` (8 weights), `matching` (5 weights)

---

## 🗄️ Database Schema (PostgreSQL — 20 tables)

### Synced from MSSQL (read-only copy)
| Table | Rows (est.) | Notes |
|-------|------------|-------|
| `synced_properties` | 35 | Approved, non-deleted properties |
| `synced_rooms` | 100 | Non-deleted, capacity tracking |
| `synced_amenities` | 35 | 14 amenity flags per property |
| `synced_allowed_tenants` | 50 | Gender/occupation restrictions |

### Owned by us
| Table | Purpose |
|-------|---------|
| `user_profiles` | Profile + college + sleep + smoking |
| `questionnaire_categories` | 4 categories |
| `questionnaire_questions` | 16 questions |
| `user_questionnaire_answers` | User answers (unique per question) |
| `user_search_preferences` | Learned + explicit preferences |
| `property_recommendations` | Cached property scores (24h TTL) |
| `room_recommendations` | Cached room scores (24h TTL) |
| `roommate_matches` | Secret compatibility scores (24h TTL) |
| `user_interactions` | Lifetime interaction log (dwell, lat/lng) |
| `scoring_weights` | 20 configurable A/B weights |
| `user_feedback_weights` | Learned boost/penalty factors |
| `property_embeddings` | Future: pgvector(384) embeddings |
| `user_embeddings` | Future: pgvector(384) embeddings |

---

## 🔄 Data Flow

### Flow 1: User views a property
```
React → ASP.NET → POST /interactions
                        │
                        ├─ Log: viewed, dwell_seconds
                        ├─ Analyzer learns preferences
                        └─ Next GET /recommend → better scores
```

### Flow 2: User answers questionnaire
```
React → ASP.NET → POST /questionnaire/answers/{user_id}
                        │
                        ├─ Save answers to PostgreSQL
                        ├─ BackgroundTasks: re-run recommendations
                        ├─ BackgroundTasks: re-run matching
                        └─ Results updated in cache
```

### Flow 3: ASP.NET wants roommate matches
```
ASP.NET → POST /match/compute/{user_id}
              │
              ├─ Load seeker's questionnaire answers
              ├─ Find all users with answers
              ├─ Compute pairwise for each room
              ├─ Aggregate room scores
              ├─ Store in roommate_matches (secret)
              └─ Return only room_compatibility_score
```

---

## 🎯 Use Cases

### Use Case 1: Property Discovery
**User** searches for apartments in Cairo under 5000 EGP.
**System** scores all 35 properties → returns top 10 ranked by budget fit + location + amenities.
**Extra:** If user dwells 45s on property #3 → next search boosts similar properties.

### Use Case 2: Roommate Compatibility
**User A** wants a shared apartment. System finds 4 candidates in 3 rooms.
**System** computes pairwise scores: A↔B (0.91), A↔C (0.45), A↔D (0.78).
**Room 1** (B is there): room_score = 0.91. **Room 2** (C, D): room_score = avg(0.45, 0.78) × capacity_factor.
**ASP.NET** only sees: room 1 → 0.91, room 2 → 0.55.

### Use Case 3: Cold Start
**New user** has no interactions, no questionnaire answers.
**System** returns neutral scores (0.5 for each factor) → properties ranked by recency.
After user views 5+ properties, `POST /analyze` infers their preferences.

### Use Case 4: A/B Testing
**Product manager** wants to test increasing budget weight from 30% to 40%.
```bash
curl -X PUT "/admin/weights/property/budget?value=0.40" -H "X-API-Key: ..."
# No deploy needed. Next recommendation uses new weight.
```

### Use Case 5: Behavioral Targeting
**User** always looks at premium properties in New Cairo, never saves anything.
**Classification:** `explorer_browser`, `premium_segment`.
**System** increases max_budget recommendation, decreases save-based scoring.

---

## 🚀 Deployment

Same stack as chatbot: **Railway (Docker) + Neon PostgreSQL**.

```bash
# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Seed questionnaire (first time only)
python scripts/seed_questionnaire.py

# Manual sync from MSSQL
python scripts/sync_data.py
```

### Environment Variables
```env
DATABASE_URL=postgresql://...?sslmode=require
MSSQL_CONNECTION_STRING=DRIVER={ODBC Driver 17}...
SYNC_INTERVAL_MINUTES=5
API_KEY=staymatch-rec-api-key-2026
LOG_LEVEL=INFO
```

---

## 🧪 Testing

```bash
PYTHONPATH=. pytest tests/ -v
# 83 tests covering all scorers, rankers, matching, schemas
```

---

## 📞 How to Talk to the Backend Team

### For ASP.NET Developers:
1. **Always pass `X-API-Key`** in all requests
2. **Sync after property CRUD:** Call `POST /sync/refresh` when properties are added/edited/deleted in your system
3. **Log ALL interactions:** Call `POST /interactions` for every user action (view, save, like, contact) including **`dwell_seconds`** (time spent on page) and **`search_lat/search_lng`** (location coordinates)
4. **Send questionnaire answers:** Call `POST /questionnaire/answers/{user_id}` — this auto-triggers recomputation
5. **Never expose `match_breakdown`**: The `/match/results` endpoint only returns `room_compatibility_score` — this is intentional
6. **Use `/analyze` after 5+ interactions:** To infer and persist user preferences
7. **Test weights in staging first:** Use `PUT /admin/weights` to tune scoring without redeploying

### For Frontend Developers:
1. The recommendation service is **private** — all calls go through ASP.NET backend, NOT directly from frontend
2. The recommendation response includes `score_breakdown` JSON — you can use this to show users WHY a property was recommended
3. The `dwell_seconds` field is critical — track how long users stay on property pages (30s+ = strong interest)

---

> Built with ❤️ by StayMatch AI Team — June 2026
