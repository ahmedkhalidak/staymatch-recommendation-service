# Roommate Matching Improvement Plan

## Analysis: Current Issues

### 1. Gender is a Weighted Feature (WRONG)
Currently in `_compute_pairwise` (`compatibility_engine.py:98-114`):
```python
return 0.7 * q_score + 0.3 * (0.4 * gender_sim + 0.3 * occupation_sim + 0.3 * age_sim)
```
Gender = 12% of total score. But the platform already enforces gender via `SyncedAllowedTenant.student_gender` / `worker_gender`. Gender should be a **hard eligibility gate** checked before any matching — not a soft weight.

### 2. Age and Occupation are Over-weighted
| Source | Current % | Analysis |
|--------|-----------|----------|
| Profile age (9%) + Q1 age group (5.6% = 8% × 70%) | **~14.6%** | Too high — age has minor impact on roommate harmony |
| Profile occ (9%) + Q2 status (8.4% = 12% × 70%) | **~17.4%** | Too high — status info is already in questionnaire |
| **Real life factors** (sleep, smoking, cleanliness) | **~44.8%** | Undervalued — these are the real sources of roommate conflict |

### 3. Redundancy Between Profile and Questionnaire
- `Q1` (age group) duplicates `UserProfile.birth_year`
- `Q2` (current status) partially duplicates `UserProfile.occupation`

### 4. Empty Room Default = 0.65
Hardcoded in `_aggregate_room_score`. Not adjustable via DB weights.

### 5. No Tenant Eligibility Check in Matching Flow
`compute_for_user` loads all rooms with `capacity_available > 0` but never checks `SyncedAllowedTenant` — a female student could be matched to a male-only room.

---

## Proposed Changes

### File-by-File Implementation

---

## File 1: `app/services/matching/feature_encoding.py`

### What changes
Redistribute questionnaire weights to favor real roommate conflict factors.

| Q# | Feature | Category | Current | **Proposed** | Rationale |
|----|---------|----------|---------|-------------|-----------|
| 1 | Age group | Personal | 0.08 | **0.03** | Redundant with profile.birth_year |
| 2 | Status | Personal | 0.12 | **0.05** | Partially redundant with profile.occupation |
| 3 | Field of study/work | Personal | 0.03 | **0.05** | Kept as user requested — good conversation starter |
| 4 | Busy time | Schedule | 0.08 | **0.10** | Important daily rhythm compatibility |
| 5 | Sleep schedule | Schedule | 0.12 | **0.14** | **Increased** — top conflict source |
| 6 | Return home | Schedule | 0.05 | **0.04** | Minor — kept as lifestyle indicator |
| 7 | Cleanliness/mess | Lifestyle | 0.12 | **0.14** | **Increased** — top conflict source |
| 8 | Free days | Lifestyle | 0.03 | **0.03** | Kept low |
| 9 | Group activities | Lifestyle | 0.08 | **0.07** | Social compatibility |
| 10 | Study/work env | Lifestyle | 0.05 | **0.08** | **Increased** — noise preference matters |
| 11 | Smoking | Social | 0.12 | **0.14** | **Increased** — critical dealbreaker |
| 12 | Frustration | Social | 0.07 | **0.05** | Diagnostic only |
| 13 | Flexibility | Social | 0.05 | **0.08** | **Increased** — mediating factor for all conflicts |
| | | **Total** | **1.00** | **1.00** | |

New weight key groups for readability:
```python
LIFESTYLE_KEYS = {4, 5, 6, 7, 8, 9, 10}  # daily life compatibility
DEALBREAKER_KEYS = {11}                    # smoking
SOCIAL_KEYS = {12, 13}                     # social/flexibility
BACKGROUND_KEYS = {1, 2, 3}               # personal background (reduced)
```

### `MAX_VALS` update
Add Q4 (busy time) which has 5 options:
```python
MAX_VALS = {1: 3, 4: 4, 5: 3, 6: 3, 7: 3, 9: 3, 10: 3, 13: 3}
# Q4 max val should be 4 (5 options indexed 0-4 or 1-5)
```
Check the actual scale. From seed: "Early morning", "Late morning", "Afternoon", "Evening", "Night" = 5 values. If indexed 0-4, `MAX_VALS[4] = 4`. If indexed 1-5, `MAX_VALS[4] = 5`.

Verify actual stored scale format before changing.

### Smoking logic
Keep current logic — it already acts as a soft dealbreaker:
- `d ≤ 1` → 1.0 (compatible stances)
- `d == 2` → 0.1 (large mismatch)
- `d ≥ 3` → 0.0 + `smoke_penalty = 0.3` (opposite = severe penalty)

---

## File 2: `app/services/matching/compatibility_engine.py`

### 2a. Add tenant eligibility check

New method — checks `SyncedAllowedTenant` for a given room against seeker:

```python
def _check_tenant_eligibility(self, seeker_profile: UserProfile | None, room: SyncedRoom) -> bool:
    """Returns False if the seeker is blocked by tenant restrictions (gender/occupation)."""
    if not seeker_profile:
        return True  # no data = can't block
    
    allowed_tenants = room.allowed_tenants
    if not allowed_tenants or len(allowed_tenants) == 0:
        return True  # no restrictions
    
    # Use the first allowed_tenant record (room-level or property-level)
    at = allowed_tenants[0]
    gender = (seeker_profile.gender or "").lower()
    gender_val = 0 if gender == "male" else (1 if gender == "female" else None)
    
    occupation = (seeker_profile.occupation or "").lower()
    is_student = occupation == "student"
    is_worker = occupation == "worker"
    
    # Gender checks through AllowedTenants
    if gender_val is not None:
        sg = getattr(at, "student_gender", None)
        wg = getattr(at, "worker_gender", None)
        
        # If room allows only one student gender, enforce it
        if sg is not None and at.allows_students:
            if sg != gender_val:
                return False
        
        # If room allows only one worker gender, enforce it
        if wg is not None and at.allows_workers:
            if wg != gender_val:
                return False
    
    # Occupation checks through AllowedTenants
    students_only = at.allows_students and not at.allows_workers and not at.allows_families
    workers_only = at.allows_workers and not at.allows_students and not at.allows_families
    
    if students_only and not is_student:
        return False
    if workers_only and not is_worker:
        return False
    
    return True
```

This mirrors the logic in `TenantScorer.score()` but returns a boolean gate instead of a score.

### 2b. Modify `compute_for_user`

Insert eligibility check in the room loop:

```python
for room in rooms:
    # --- NEW: Hard Filter Step ---
    if not self._check_tenant_eligibility(seeker_profile, room):
        continue  # skip this room entirely, score = 0, not included
    
    occupants = get_current_room_occupants(room.id)
    ...
```

Empty room logic stays the same (0.65 default).

### 2c. Update `_compute_pairwise`

Remove gender. Keep questionnaire + occupation + age:

```python
def _compute_pairwise(self, answers_a: dict, answers_b: dict, profile_a=None, profile_b=None) -> float:
    q_score = weighted_similarity(answers_a, answers_b)
    
    occupation_sim = 1.0
    if profile_a and profile_b and profile_a.occupation and profile_b.occupation:
        occupation_sim = 1.0 if profile_a.occupation.lower() == profile_b.occupation.lower() else 0.5
    
    age_sim = 1.0
    if profile_a and profile_b and profile_a.birth_year and profile_b.birth_year:
        age_diff = abs(profile_a.birth_year - profile_b.birth_year)
        age_sim = max(0.0, 1.0 - age_diff / 20.0)
    
    return 0.85 * q_score + 0.08 * occupation_sim + 0.07 * age_sim
```

### 2d. Update `_profile_only_score`

Remove gender:

```python
def _profile_only_score(self, profile_a, profile_b) -> float:
    if not profile_a or not profile_b:
        return 0.5
    occ = 1.0 if (profile_a.occupation or "").lower() == (profile_b.occupation or "").lower() else 0.5
    age = 0.5
    if profile_a.birth_year and profile_b.birth_year:
        age = max(0.0, 1.0 - abs(profile_a.birth_year - profile_b.birth_year) / 20.0)
    return 0.6 * occ + 0.4 * age
```

### 2e. Update `_aggregate_room_score` — optional

Consider making empty room default configurable. For now keep 0.65 but add a TODO to make it loadable from `scoring_weights` table. Or better: change to a neutral 0.5 since an empty room is not inherently good or bad.

Decision: **Keep 0.65** — it signals opportunity without being perfect. Can be tuned later.

---

## File 3: `app/utils/weights.py`

### Update MATCHING_WEIGHTS

```python
MATCHING_WEIGHTS = {
    "questionnaire": 0.85,
    "occupation":     0.08,
    "age_group":      0.07,
}
```

Remove `"gender": 0.12` entirely — gender is now a hard filter.

---

## File 4: `app/services/recommendation/property_recommender.py`

### 4a. Update `_get_roommate_score`

Add tenant eligibility check before computing pairwise scores:

```python
def _get_roommate_score(self, user_id, room):
    if not user_id:
        return 0.5
    
    # === NEW: Hard filter ===
    seeker_profile = self.compat_engine.session.query(UserProfile).filter(
        UserProfile.external_user_id == user_id
    ).first()
    if not self.compat_engine._check_tenant_eligibility(seeker_profile, room):
        return 0.0  # blocked
    
    occupants = get_current_room_occupants(room.id)
    if not occupants:
        return 0.65
    ...
```

Then follow same pattern: use updated `_compute_pairwise` (no gender).

---

## File 5: `scripts/seed_questionnaire.py`

### Adjust question weights to match new feature_encoding.py

Update the `weight` field in each question dict:

```python
{"category": 1, "weight": 0.03, ...},  # Q1: age (reduced)
{"category": 1, "weight": 0.05, ...},  # Q2: status (reduced)
{"category": 1, "weight": 0.05, ...},  # Q3: field (kept per request)
{"category": 2, "weight": 0.10, ...},  # Q4: busy time (increased)
{"category": 2, "weight": 0.14, ...},  # Q5: sleep (increased)
{"category": 2, "weight": 0.04, ...},  # Q6: return home (slightly reduced)
{"category": 3, "weight": 0.14, ...},  # Q7: cleanliness (increased)
{"category": 3, "weight": 0.03, ...},  # Q8: free days (kept)
{"category": 3, "weight": 0.07, ...},  # Q9: group activities (slightly reduced)
{"category": 3, "weight": 0.08, ...},  # Q10: study env (increased)
{"category": 4, "weight": 0.14, ...},  # Q11: smoking (increased)
{"category": 4, "weight": 0.05, ...},  # Q12: frustration (reduced)
{"category": 4, "weight": 0.08, ...},  # Q13: flexibility (increased)
```

Note: Change `weight` values only — do NOT modify question text, options, or structure. The user explicitly said to keep Q3 (field of study).

---

## File 6: `tests/test_matching.py`

All 12 failing tests need to be rewritten. Key changes:

1. Replace all `_questionnaire_similarity` calls with `weighted_similarity` from `feature_encoding`
2. `_aggregate_room_score` now takes 3 params: `(pairwise_scores, total_capacity, occupant_count)` — update test calls
3. Remove gender from pairwise computation tests
4. Add new test: `test_tenant_eligibility_blocks_gender_mismatch` and `test_tenant_eligibility_passes`
5. Add new test: `test_new_weight_distribution_matches_expected`

---

## Summary of New Matching Formula

```
Step 1: Hard Filters (Gate)
├── Gender × AllowedTenants (student_gender / worker_gender)
└── Occupation × AllowedTenants (allows_students / allows_workers / allows_families)
    If blocked → score = 0, room excluded entirely

Step 2: Weighted Compatibility (if gate passes)
├── Questionnaire Similarity (85%)
│   ├── Sleep Schedule (Q5)         14%
│   ├── Cleanliness (Q7)            14%
│   ├── Smoking (Q11)               14%
│   ├── Busy Time (Q4)              10%
│   ├── Social/Group (Q9)            7%
│   ├── Flexibility (Q13)            8%
│   ├── Study Environment (Q10)      8%
│   ├── Frustration (Q12)            5%
│   ├── Status (Q2)                  5%
│   ├── Field of Study (Q3)          5%
│   ├── Return Home (Q6)             4%
│   ├── Free Days (Q8)               3%
│   └── Age Group (Q1)               3%
├── Occupation (profile)              8%
└── Age (profile)                     7%
    Total = 100%

Step 3: Room-Level Aggregation
Score = 0.6 × min(pairwise_scores) + 0.4 × avg(pairwise_scores) + empty_slot_bonus
```