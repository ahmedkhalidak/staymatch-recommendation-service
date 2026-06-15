"""Runtime verification script - executes actual code paths to document real behavior."""
import asyncio
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/ahmed-khalid/AHMED-Projects-2026/staymatch-recommendation-service')

from app.database.session import get_session
from app.database.models.user import QuestionnaireQuestion, UserQuestionnaireAnswer, UserProfile
from app.database.models.property import SyncedProperty, SyncedRoom
from app.services.matching.compatibility_engine import CompatibilityEngine
from app.services.matching.feature_encoding import load_questionnaire_weights_and_metadata
from app.services.property_api_client import get_property_api_client
from app.repositories.questionnaire_repo import QuestionnaireRepository
from sqlalchemy import text

print("=" * 80)
print("RUNTIME VERIFICATION - StayMatch Recommendation Service")
print("=" * 80)
print(f"Started at: {datetime.utcnow()}")
print()

# Step 1: Database Connection Verification
print("STEP 1: Database Connection")
print("-" * 80)
try:
    session = get_session()
    result = session.execute(text("SELECT 1")).scalar()
    print(f"✓ PostgreSQL connection: SUCCESS (result: {result})")
    session.close()
except Exception as e:
    print(f"✗ PostgreSQL connection: FAILED - {e}")
    sys.exit(1)

# Step 2: Check Database Tables
print("\nSTEP 2: Database Tables Verification")
print("-" * 80)

tables_to_check = [
    "questionnaire_categories",
    "questionnaire_questions",
    "user_questionnaire_answers",
    "user_profiles",
    "synced_properties",
    "synced_rooms",
    "synced_amenities",
    "synced_allowed_tenants",
    "property_recommendations",
    "room_recommendations",
    "user_interactions",
    "scoring_weights",
]

for table in tables_to_check:
    try:
        session = get_session()
        result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"✓ {table}: {result} rows")
        session.close()
    except Exception as e:
        print(f"✗ {table}: ERROR - {str(e)[:100]}")
        try:
            session.close()
        except:
            pass

# Step 3: Questionnaire Data
print("\nSTEP 3: Questionnaire Data")
print("-" * 80)
session = get_session()
questions = session.query(QuestionnaireQuestion).filter(
    QuestionnaireQuestion.is_active == True
).order_by(QuestionnaireQuestion.id).all()

print(f"Total active questions: {len(questions)}")
print("\nQuestion Details:")
for q in questions:
    print(f"  ID {q.id}: {q.question_en[:50]}...")
    print(f"    Type: {q.question_type}, Weight: {q.weight}")
    print(f"    Options (EN): {q.options_en}")
    print(f"    Matching Key: {getattr(q, 'matching_key', 'NOT SET')}")
    print()

# Step 4: Load Question Weights and Metadata
print("\nSTEP 4: Question Weights and Metadata")
print("-" * 80)
weights, metadata, smoking_question_id = load_questionnaire_weights_and_metadata()
print(f"Smoking question ID: {smoking_question_id}")
print(f"\nWeights (question_id -> weight):")
for qid, w in sorted(weights.items()):
    print(f"  Question {qid}: {w}")

print(f"\nMetadata sample (first 3 questions):")
for qid, meta in list(sorted(metadata.items()))[:3]:
    print(f"  Question {qid}:")
    print(f"    Type: {meta.get('question_type')}")
    print(f"    Options: {meta.get('options_en')}")
    print(f"    Matching Key: {meta.get('matching_key')}")

# Step 5: Check Properties 122, 123, 138
print("\nSTEP 5: Properties 122, 123, 138 Verification")
print("-" * 80)
property_ids = [122, 123, 138]
for pid in property_ids:
    prop = session.query(SyncedProperty).filter(SyncedProperty.id == pid).first()
    if prop:
        print(f"\n✓ Property {pid}:")
        print(f"  Name: {prop.name}")
        print(f"  City: {prop.city}")
        print(f"  Government: {prop.government}")
        print(f"  Monthly Rent: {prop.monthly_rent}")
        print(f"  Property Type: {prop.property_type}")
        print(f"  Is Approved: {prop.is_approved}")
        
        # Check rooms
        rooms = session.query(SyncedRoom).filter(
            SyncedRoom.property_id == pid,
            SyncedRoom.is_deleted == False
        ).all()
        print(f"  Rooms: {len(rooms)}")
        for room in rooms:
            print(f"    Room {room.id}: {room.room_name}, Capacity: {room.capacity}, Available: {room.capacity_available}")
    else:
        print(f"\n✗ Property {pid}: NOT FOUND in synced_properties")

session.close()

# Step 6: Test External API Connection
print("\nSTEP 6: External API Connection")
print("-" * 80)
api_client = get_property_api_client()
print(f"API Base URL: {api_client.base_url}")
print(f"API Token: {'SET' if api_client.token else 'NOT SET'}")

async def test_api():
    try:
        # Test property existence
        result = await api_client.property_exists(122)
        print(f"✓ Property 122 exists check: {result}")
        
        # Test get property occupants
        occupants = await api_client.get_property_occupants(122)
        print(f"✓ Property 122 occupants: {len(occupants)} occupants")
        if occupants:
            for occ in occupants[:3]:
                print(f"    User ID: {occ.get('userId')}, Room ID: {occ.get('roomId')}")
        
        # Test room occupants
        if occupants and occupants[0].get('roomId'):
            room_occupants = await api_client.get_room_occupants(occupants[0]['roomId'])
            print(f"✓ Room {occupants[0]['roomId']} occupants: {room_occupants}")
            
    except Exception as e:
        print(f"✗ API Test FAILED: {e}")

asyncio.run(test_api())

# Step 7: Compatibility Engine Initialization
print("\nSTEP 7: Compatibility Engine Initialization")
print("-" * 80)
try:
    engine = CompatibilityEngine()
    print("✓ CompatibilityEngine initialized")
    print(f"  Smoking question ID: {engine.smoking_question_id}")
    print(f"  Age question ID: {engine.age_question_id}")
    print(f"  Occupation question ID: {engine.occupation_question_id}")
except Exception as e:
    print(f"✗ CompatibilityEngine initialization FAILED: {e}")

# Step 8: Check User Answers
print("\nSTEP 8: User Questionnaire Answers")
print("-" * 80)
from sqlalchemy import func
session = get_session()
answers = session.query(UserQuestionnaireAnswer).limit(10).all()
print(f"Total answers in DB: {session.query(UserQuestionnaireAnswer).count()}")
print(f"\nSample answers (first 10):")
for ans in answers:
    print(f"  User: {ans.user_id}, Question: {ans.question_id}, Answer: {ans.answer_value} (scale: {ans.answer_scale})")

# Get users with most answers
user_answer_counts = session.query(
    UserQuestionnaireAnswer.user_id,
    func.count(UserQuestionnaireAnswer.id).label('count')
).group_by(UserQuestionnaireAnswer.user_id).order_by(func.count(UserQuestionnaireAnswer.id).desc()).limit(5).all()
print(f"\nTop 5 users by answer count:")
for user_id, count in user_answer_counts:
    print(f"  {user_id}: {count} answers")

session.close()

print("\n" + "=" * 80)
print("RUNTIME VERIFICATION COMPLETE")
print("=" * 80)
print(f"Completed at: {datetime.utcnow()}")
