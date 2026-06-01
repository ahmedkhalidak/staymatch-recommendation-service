The recommendation service already has `database/session.py` with PostgreSQL engine + MSSQL engine setup.

**Key models and their relationships:**
- `synced_properties` ← `synced_rooms` (one-to-many via property_id)
- `synced_properties` ← `synced_amenities` (one-to-one via property_id)
- `synced_properties` ← `synced_allowed_tenants` (one-to-many via property_id)
- `synced_rooms` ← `synced_allowed_tenants` (one-to-many via room_id)
- `synced_properties` ← `property_recommendations` (one-to-many)
- `synced_rooms` ← `room_recommendations` (one-to-many)
- `synced_rooms` ← `roommate_matches` (one-to-many)

**Scoring pipeline:**
1. Load user profile + preferences + questionnaire answers
2. Load candidate pool (approved properties / available rooms)
3. Run each BaseScorer (budget, location, amenities, tenant, questionnaire)
4. Ranker computes weighted sum using configurable weights
5. Apply diversity rule (max 2 per property for rooms)
6. Cache results in recommendation tables

**Matching secrecy:** The `roommate_matches` table stores `match_breakdown` with individual pairwise scores internally. The API returns ONLY `room_compatibility_score` — never individual scores. This is enforced in the API layer at `/match/results/{user_id}`.