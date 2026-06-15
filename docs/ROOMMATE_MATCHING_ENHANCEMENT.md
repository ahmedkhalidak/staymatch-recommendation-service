# Roommate Matching Enhancement - Schema Analysis

## Current RoommateMatch Schema

```python
class RoommateMatch(Base):
    __tablename__ = "roommate_matches"
    
    id = Column(Integer, primary_key=True)
    seeker_user_id = Column(String(255), nullable=False)
    room_id = Column(Integer, ForeignKey("synced_rooms.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("synced_properties.id"), nullable=False)
    room_compatibility_score = Column(Float, nullable=False)
    match_breakdown = Column(JSONB)
    current_roommates = Column(JSONB)
    seeker_questionnaire_match = Column(Float)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime)
    
    __table_args__ = (
        UniqueConstraint("seeker_user_id", "room_id"),
    )
```

## Current Limitations

1. **One row per room per seeker** - The unique constraint is on (seeker_user_id, room_id)
2. **No property-level score** - Only room_compatibility_score exists
3. **No room aggregation** - Can't easily get all room scores for a property

## Proposed Schema Changes

### Option 1: Add property_match_score Column (Recommended)

**Changes:**
- Add `property_match_score` column to RoommateMatch table
- Keep existing structure (one row per room per seeker)
- Property score will be the same across all rooms in the same property

**Migration:**
```sql
ALTER TABLE roommate_matches 
ADD COLUMN property_match_score FLOAT;

CREATE INDEX idx_match_property_score ON roommate_matches(property_match_score DESC);
```

**Pros:**
- Minimal schema change
- Backward compatible
- Simple to implement
- Existing queries continue to work

**Cons:**
- Property score duplicated across rooms (data redundancy)
- Slightly larger storage

**Example Data:**
```
seeker_user_id | room_id | property_id | room_compatibility_score | property_match_score
user1          | 221     | 138        | 0.85                    | 0.82
user1          | 222     | 138        | 0.75                    | 0.82
user1          | 223     | 138        | 0.78                    | 0.82
```

### Option 2: Separate PropertyMatch Table

**New Table:**
```python
class PropertyMatch(Base):
    __tablename__ = "property_matches"
    
    id = Column(Integer, primary_key=True)
    seeker_user_id = Column(String(255), nullable=False)
    property_id = Column(Integer, ForeignKey("synced_properties.id"), nullable=False)
    property_match_score = Column(Float, nullable=False)
    match_breakdown = Column(JSONB)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime)
    
    __table_args__ = (
        UniqueConstraint("seeker_user_id", "property_id"),
    )
```

**Pros:**
- No data duplication
- Clean separation of concerns
- One row per property per seeker

**Cons:**
- More complex queries (need joins)
- Two tables to maintain
- More complex deletion logic

### Option 3: Restructure to One Row Per Property

**Changes:**
- Change unique constraint to (seeker_user_id, property_id)
- Store room_scores in JSONB column
- Remove room_id FK (or make it nullable)

**Pros:**
- One row per property per seeker
- All room scores in one place

**Cons:**
- Breaking change to existing data
- More complex JSONB queries
- Harder to query by room_id
- Requires data migration

## Recommendation

**Use Option 1: Add property_match_score column**

### Rationale

1. **Minimal disruption** - Simple column addition, no restructuring
2. **Backward compatible** - Existing code continues to work
3. **Simple implementation** - No complex joins or JSONB queries
4. **Acceptable redundancy** - Property score duplication is minor (same property_id groups share the same score)
5. **Easy to query** - Can still query by room_id or property_id

### Query Patterns

**Get property-level match:**
```sql
SELECT property_id, property_match_score
FROM roommate_matches
WHERE seeker_user_id = 'user1' AND property_id = 138
LIMIT 1;
```

**Get all room scores for a property:**
```sql
SELECT room_id, room_compatibility_score
FROM roommate_matches
WHERE seeker_user_id = 'user1' AND property_id = 138;
```

**Get property with room scores (API response):**
```sql
SELECT 
    property_id,
    MAX(property_match_score) as property_match_score,
    json_agg(
        json_build_object(
            'room_id', room_id,
            'room_match_score', room_compatibility_score,
            'occupants_count', jsonb_array_length(current_roommates)
        )
    ) as rooms
FROM roommate_matches
WHERE seeker_user_id = 'user1' AND property_id = 138
GROUP BY property_id;
```

## Implementation Plan

1. **Add migration** to add property_match_score column
2. **Update CompatibilityEngine** to calculate property-level compatibility
3. **Update MatchingRepository** to save property_match_score
4. **Update API response** to include property and room scores
