# StayMatch AI Service — Simple Guide

Two things only:

**1. Matching** — user vs user (from bookings), using questionnaire answers with weighted similarity → score

**2. Recommendation** — user vs property/room, using reviews + content + location → score

---

## 1. Matching (User ↔ User)

### How it works

```
Booking table (MSSQL) → who lives in each room → compare seeker vs each occupant
                                                                  ↓
                                                     questionnaire answers → weighted similarity → score
```

### Step by step

1. For each room, get current occupants from `Bookings`:
   ```sql
   SELECT UserId FROM Bookings 
   WHERE RoomId = ? AND Status = 'Approved' AND EndDate >= TODAY
   ```

2. Compare seeker vs each occupant using questionnaire answers:

   | Question | Type | Options | Weight |
   |----------|------|---------|--------|
   | Age group | ordered | under20 / 20-24 / 25-30 / 30+ | 0.08 |
   | Status | nominal | Student / Employee / Freelancer / Working&Studying | 0.12 |
   | Field | nominal | Eng / Med / IT / Business / Arts / Edu / Law / Other | 0.03 |
   | Busy time | ordered | Early morn / Late morn / Afternoon / Evening / Night | 0.08 |
   | Sleep time | ordered | Before10PM / 10-12 / 12-2AM / After2AM | 0.12 |
   | First action home | ordered | Wash / Go room / Eat / Socialize | 0.05 |
   | Mess reaction | ordered | Clean now / Annoyed / When time / Don't care | 0.12 |
   | Free days | nominal | Home / Friends / Study / Hobbies / Family | 0.03 |
   | Group activities | ordered | Love / Sometimes / Rarely / Alone | 0.08 |
   | Work environment | ordered | Quiet / Moderate / Cafe / Flexible | 0.05 |
   | Smoking | **dealbreaker** | Non prefers non / Non ok / Smoker ok / Smoker prefers smoker | 0.12 |
   | Biggest frustration | nominal | Mess / Noise / Bills / Privacy / Schedule | 0.07 |
   | Flexibility | ordered | Very / Somewhat / Prefer similar / Must match | 0.05 |

3. Score formula:
   ```
   For each shared question:
     ordered:  1 - |val_a - val_b| / max_val
     nominal:  1 if same, 0 if different
     smoking:  1 if diff≤1, 0.1 if diff=2, 0 if diff≥3
   
   total = Σ(weight × sim) / Σ(weight) × smoking_penalty
   
   smoking_penalty = 0.3 if smoking_diff ≥ 2, else 1.0
   ```

4. If occupant has NO questionnaire answers, fallback to profile-only:
   ```
   score = 0.4 × gender_match + 0.3 × occupation_match + 0.3 × age_sim
   ```

5. Room score = worst occupant matters most:
   ```
   room_score = 0.6 × min(pairwise_scores) + 0.4 × avg(pairwise_scores) + empty_bonus
   empty_bonus = min(0.1, empty_beds × 0.03)
   ```

6. Final output:
   ```json
   {
     "room_id": 42,
     "room_compatibility_score": 0.88,
     "explanation": "88% — similar sleep schedules, same smoking preference",
     "occupants": [
       {"user_id": "abc", "score": 0.88},
       {"user_id": "def", "score": 0.75}
     ]
   }
   ```

---

## 2. Recommendation (User ↔ Property/Room)

### Property scoring factors

| Factor | Weight | How it works |
|--------|--------|-------------|
| Budget | 0.25 | Rent inside range=1.0, up to 20% over=0.7, more=decay |
| Location | 0.20 | Same city=1.0, nearby gov=0.5+, far=0.0 |
| Amenities | 0.12 | % of wanted amenities matched |
| Tenant rules | 0.10 | Gender/occupation match=1.0, block=0.0 |
| Furnished | 0.05 | Yes=1.0, No=0.5 |
| Property type | 0.08 | Full vs shared match |
| Recency | 0.05 | New listing=1.0, old=decay |
| Reviews | 0.10 | Avg rating, bayesian smoothed |
| Questionnaire | 0.05 | Type preference match |

```
total = weighted_sum(all factors)
```

### Room scoring factors

| Factor | Weight | How it works |
|--------|--------|-------------|
| Budget | 0.20 | Same as property |
| Location | 0.15 | From parent property |
| Capacity | 0.08 | Partially filled=best |
| Amenities | 0.10 | From parent property |
| Tenant rules | 0.08 | Same as property |
| Furnished | 0.05 | Yes=1.0, No=0.5 |
| Room type | 0.10 | Ensuite=+0.3, Balcony=+0.1, Window=+0.1 |
| Recency | 0.04 | New=1.0, old=decay |
| Roommate compat | 0.15 | From matching (section 1) |
| Property rating | 0.05 | From parent property reviews |

```
total = weighted_sum(all factors)
```

### Cold start (no user data)

Show popular properties based on most-viewed + most-saved + newest listings.

### Diversity caps

- Max 3 properties per city
- Max 2 rooms per property

---

## 3. Files to change

| File | What to change |
|------|---------------|
| `app/services/mssql_reader.py` | Add `get_current_room_occupants()` and `get_room_occupants_batch()` |
| `app/services/matching/feature_encoding.py` | NEW — 13-question encoding + weighted similarity |
| `app/services/matching/compatibility_engine.py` | Rewrite to use booking occupants + profile fallback |
| `app/services/recommendation/property_recommender.py` | Add roommate_compat factor to room scorer |
| `app/utils/weights.py` | Update weights to match tables above |
| `scripts/seed_questionnaire.py` | Replace with the 13 questions above |
| `app/api/router.py` | Add API key check, fix feedback endpoint |

---

## 4. Quick start commands

```bash
# Run tests
PYTHONPATH=. python -m pytest tests/ -v

# Seed new questionnaire
PYTHONPATH=. python scripts/seed_questionnaire.py

# Start server
uvicorn app.main:app --reload --port 8000

# Test matching
curl -X POST http://localhost:8000/match/compute/user-123 \
  -H "X-API-Key: your-key"

# Test recommendations
curl http://localhost:8000/recommend/rooms/user-123?limit=10 \
  -H "X-API-Key: your-key"
curl http://localhost:8000/recommend/properties/user-123?limit=10 \
  -H "X-API-Key: your-key"
```