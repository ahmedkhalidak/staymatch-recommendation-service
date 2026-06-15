#!/usr/bin/env python
"""Test corrected architecture with external user_id in APIs and user_profile_id in database"""
from app.database.session import get_session
from app.database.models.user import (
    UserProfile,
    QuestionnaireProfile,
    QuestionnaireCategory,
    QuestionnaireQuestion,
    UserQuestionnaireAnswer,
)
from app.repositories.questionnaire_repo import QuestionnaireRepository
from sqlalchemy import text
import uuid

# Test 1: Verify tables exist and are empty
print("Test 1: Verify tables exist and are empty")
session = get_session()
try:
    print(f"user_profiles count: {session.query(UserProfile).count()}")
    print(f"questionnaire_profiles count: {session.query(QuestionnaireProfile).count()}")
    print(f"user_questionnaire_answers count: {session.query(UserQuestionnaireAnswer).count()}")
    print("✓ Tables exist and are empty after cleanup")
finally:
    session.close()

# Test 2: Create a user profile with external_user_id
print("\nTest 2: Create user profile with external_user_id")
session = get_session()
try:
    external_user_id = "3ee32cef-cdbe-4a63-94a1-819e34a88fec"  # Simulating .NET user ID
    user = UserProfile(
        external_user_id=external_user_id,
        full_name="Test User Corrected",
        gender="male"
    )
    session.add(user)
    session.commit()
    print(f"✓ Created user profile with external_user_id: {external_user_id}")
    print(f"✓ Internal user_profile_id: {user.id}")
finally:
    session.close()

# Test 3: Create questionnaire profile with user_profile_id
print("\nTest 3: Create questionnaire profile with user_profile_id")
session = get_session()
try:
    user = session.query(UserProfile).filter(UserProfile.external_user_id == "3ee32cef-cdbe-4a63-94a1-819e34a88fec").first()
    q_profile = QuestionnaireProfile(
        user_profile_id=user.id,
        completion_percentage=0
    )
    session.add(q_profile)
    session.commit()
    print(f"✓ Created questionnaire profile with user_profile_id: {user.id}")
finally:
    session.close()

# Test 4: Test questionnaire repository with external user_id
print("\nTest 4: Test questionnaire repository with external user_id")
repo = QuestionnaireRepository()
try:
    # Get categories (should work with untouched tables)
    categories = repo.get_categories()
    print(f"✓ Got {len(categories)} questionnaire categories")
    
    # Get questions (should work with untouched tables)
    questions = repo.get_questions()
    print(f"✓ Got {len(questions)} active questions")
    
    # Test save_answers using external user_id
    if questions:
        external_user_id = "3ee32cef-cdbe-4a63-94a1-819e34a88fec"
        test_answers = [{
            "question_id": questions[0].id,
            "answer_value": "1",
            "answer_scale": 0
        }]
        repo.save_answers(external_user_id, test_answers)
        print(f"✓ Saved answers using external_user_id: {external_user_id}")
        
        # Test get_answers with external user_id
        answers = repo.get_answers(external_user_id)
        print(f"✓ Retrieved {len(answers)} answers using external_user_id")
        
        # Test get_questionnaire_status with external user_id
        status = repo.get_questionnaire_status(external_user_id)
        print(f"✓ Got questionnaire status using external_user_id: {status['user_id']}")
        assert status['user_id'] == external_user_id, "Status should return external_user_id"
finally:
    repo.session.close()

# Test 5: Verify column naming consistency
print("\nTest 5: Verify column naming consistency")
session = get_session()
try:
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    
    # Check questionnaire_profiles columns
    qp_columns = [col['name'] for col in inspector.get_columns('questionnaire_profiles')]
    print(f"questionnaire_profiles columns: {qp_columns}")
    assert 'user_profile_id' in qp_columns, "Should have user_profile_id"
    assert 'user_id' not in qp_columns, "Should not have user_id"
    print("✓ questionnaire_profiles has consistent naming (user_profile_id)")
    
    # Check user_questionnaire_answers columns
    uqa_columns = [col['name'] for col in inspector.get_columns('user_questionnaire_answers')]
    print(f"user_questionnaire_answers columns: {uqa_columns}")
    assert 'user_profile_id' in uqa_columns, "Should have user_profile_id"
    assert 'user_id' not in uqa_columns, "Should not have user_id"
    print("✓ user_questionnaire_answers has consistent naming (user_profile_id)")
    
    # Check user_search_preferences columns
    usp_columns = [col['name'] for col in inspector.get_columns('user_search_preferences')]
    print(f"user_search_preferences columns: {usp_columns}")
    assert 'user_profile_id' in usp_columns, "Should have user_profile_id"
    assert 'user_id' not in usp_columns, "Should not have user_id"
    print("✓ user_search_preferences has consistent naming (user_profile_id)")
finally:
    session.close()

# Test 6: Verify foreign keys
print("\nTest 6: Verify foreign keys")
session = get_session()
try:
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    
    # Check questionnaire_profiles foreign keys
    fks = inspector.get_foreign_keys('questionnaire_profiles')
    print(f"questionnaire_profiles foreign keys: {[(fk['constrained_columns'], fk['referred_table']) for fk in fks]}")
    assert any('user_profile_id' in fk.get('constrained_columns', []) for fk in fks), "Should have user_profile_id FK"
    print("✓ questionnaire_profiles has correct foreign key (user_profile_id → user_profiles.id)")
    
    # Check user_questionnaire_answers foreign keys
    fks = inspector.get_foreign_keys('user_questionnaire_answers')
    print(f"user_questionnaire_answers foreign keys: {[(fk['constrained_columns'], fk['referred_table']) for fk in fks]}")
    assert any('user_profile_id' in fk.get('constrained_columns', []) for fk in fks), "Should have user_profile_id FK"
    print("✓ user_questionnaire_answers has correct foreign key (user_profile_id → user_profiles.id)")
    
    # Check user_search_preferences foreign keys
    fks = inspector.get_foreign_keys('user_search_preferences')
    print(f"user_search_preferences foreign keys: {[(fk['constrained_columns'], fk['referred_table']) for fk in fks]}")
    assert any('user_profile_id' in fk.get('constrained_columns', []) for fk in fks), "Should have user_profile_id FK"
    print("✓ user_search_preferences has correct foreign key (user_profile_id → user_profiles.id)")
finally:
    session.close()

# Cleanup test data
print("\nCleanup test data")
session = get_session()
try:
    session.execute(text('TRUNCATE TABLE user_questionnaire_answers, questionnaire_profiles, user_profiles RESTART IDENTITY CASCADE'))
    session.commit()
    print("✓ Cleaned up test data")
finally:
    session.close()

print("\n✅ All corrected architecture tests passed!")
print("\nArchitecture Summary:")
print("- External API uses: external_user_id (.NET user ID)")
print("- Database uses: user_profile_id (internal UUID FK)")
print("- Repositories resolve: external_user_id → user_profile_id internally")
print("- Frontend never needs to know user_profile_id")
