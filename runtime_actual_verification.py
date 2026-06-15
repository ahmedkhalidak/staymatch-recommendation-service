"""Runtime verification of ACTUAL database state and code behavior."""
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, '/home/ahmed-khalid/AHMED-Projects-2026/staymatch-recommendation-service')

from app.database.session import get_session
from app.database.models.user import QuestionnaireQuestion, UserQuestionnaireAnswer, UserProfile, QuestionnaireCategory
from sqlalchemy import text, func

print("=" * 80)
print("RUNTIME VERIFICATION - ACTUAL DATABASE STATE")
print("=" * 80)
print(f"Started at: {datetime.utcnow()}")
print()

# Step 1: Database Connection
print("STEP 1: Database Connection")
print("-" * 80)
session = get_session()
result = session.execute(text("SELECT 1")).scalar()
print(f"✓ PostgreSQL connection: SUCCESS (result: {result})")

# Step 2: Actual Database Tables
print("\nSTEP 2: Actual Database Tables")
print("-" * 80)
tables = session.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")).fetchall()

for row in tables:
    table_name = row[0]
    count_result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    print(f"  {table_name}: {count_result} rows")

# Step 3: Questionnaire Categories
print("\nSTEP 3: Questionnaire Categories")
print("-" * 80)
categories = session.query(QuestionnaireCategory).order_by(QuestionnaireCategory.sort_order).all()
print(f"Total categories: {len(categories)}")
for cat in categories:
    print(f"  ID {cat.id}: {cat.name_en} (sort: {cat.sort_order})")

# Step 4: Questionnaire Questions
print("\nSTEP 4: Questionnaire Questions")
print("-" * 80)
questions = session.query(QuestionnaireQuestion).filter(
    QuestionnaireQuestion.is_active == True
).order_by(QuestionnaireQuestion.id).all()

print(f"Total active questions: {len(questions)}")
print("\nQuestion Details:")
for q in questions:
    print(f"  ID {q.id}: {q.question_en[:60]}...")
    print(f"    Category ID: {q.category_id}")
    print(f"    Type: {q.question_type}")
    print(f"    Weight: {q.weight}")
    print(f"    Options (EN): {q.options_en}")
    print(f"    Matching Key: {getattr(q, 'matching_key', 'NOT SET')}")
    print()

# Step 5: User Questionnaire Answers
print("\nSTEP 5: User Questionnaire Answers")
print("-" * 80)
total_answers = session.query(UserQuestionnaireAnswer).count()
print(f"Total answers in DB: {total_answers}")

if total_answers > 0:
    # Sample answers
    sample_answers = session.query(UserQuestionnaireAnswer).limit(5).all()
    print(f"\nSample answers (first 5):")
    for ans in sample_answers:
        print(f"  User: {ans.user_id}, Question: {ans.question_id}, Answer: {ans.answer_value} (scale: {ans.answer_scale}), Answered: {ans.answered_at}")

    # Users with most answers
    user_answer_counts = session.query(
        UserQuestionnaireAnswer.user_id,
        func.count(UserQuestionnaireAnswer.id).label('count')
    ).group_by(UserQuestionnaireAnswer.user_id).order_by(func.count(UserQuestionnaireAnswer.id).desc()).limit(5).all()
    print(f"\nTop 5 users by answer count:")
    for user_id, count in user_answer_counts:
        print(f"  {user_id}: {count} answers")
else:
    print("  No answers found in database")

# Step 6: User Profiles
print("\nSTEP 6: User Profiles")
print("-" * 80)
total_profiles = session.query(UserProfile).count()
print(f"Total user profiles: {total_profiles}")

if total_profiles > 0:
    sample_profiles = session.query(UserProfile).limit(3).all()
    print(f"\nSample profiles (first 3):")
    for profile in sample_profiles:
        print(f"  External ID: {profile.external_user_id}")
        print(f"  Name: {profile.full_name}")
        print(f"  Gender: {profile.gender}")
        print(f"  Birth Year: {profile.birth_year}")
        print(f"  Occupation: {profile.occupation}")
        print()

# Step 7: Scoring Weights
print("\nSTEP 7: Scoring Weights")
print("-" * 80)
try:
    weights = session.execute(text("SELECT * FROM scoring_weights")).fetchall()
    print(f"Total scoring weights: {len(weights)}")
    for row in weights:
        print(f"  Key: {row[1]}, Value: {row[2]}, Group: {row[3]}")
except Exception as e:
    print(f"Error reading scoring_weights: {e}")

# Step 8: User Interactions
print("\nSTEP 8: User Interactions")
print("-" * 80)
try:
    total_interactions = session.execute(text("SELECT COUNT(*) FROM user_interactions")).scalar()
    print(f"Total user interactions: {total_interactions}")
    
    if total_interactions > 0:
        sample_interactions = session.execute(text("""
            SELECT user_id, target_type, target_id, action, dwell_seconds, created_at 
            FROM user_interactions 
            ORDER BY created_at DESC 
            LIMIT 5
        """)).fetchall()
        
        print(f"\nSample interactions (latest 5):")
        for row in sample_interactions:
            print(f"  User: {row[0]}, Target: {row[1]}:{row[2]}, Action: {row[3]}, Dwell: {row[4]}s, Time: {row[5]}")
except Exception as e:
    print(f"Error reading user_interactions: {e}")

# Step 9: Missing Tables Check
print("\nSTEP 9: Missing Tables (Referenced in Code)")
print("-" * 80)
expected_tables = [
    "synced_properties",
    "synced_rooms", 
    "synced_amenities",
    "synced_allowed_tenants",
    "property_recommendations",
    "room_recommendations",
]

actual_tables = [row[0] for row in tables]

for table in expected_tables:
    if table in actual_tables:
        print(f"  ✓ {table}: EXISTS")
    else:
        print(f"  ✗ {table}: MISSING (code references this table)")

# Step 10: Chatbot Tables (Unexpected)
print("\nSTEP 10: Chatbot-Related Tables (Unexpected in Recommendation Service)")
print("-" * 80)
chatbot_tables = [
    "conversations",
    "messages",
    "search_history",
    "session_analytics",
]

for table in chatbot_tables:
    if table in actual_tables:
        count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table}: {count} rows")

session.close()

print("\n" + "=" * 80)
print("RUNTIME VERIFICATION COMPLETE")
print("=" * 80)
print(f"Completed at: {datetime.utcnow()}")
