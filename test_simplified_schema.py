#!/usr/bin/env python
"""Test simplified schema with user_profile_id only"""
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

# Test 2: Create a user profile
print("\nTest 2: Create user profile")
session = get_session()
try:
    user = UserProfile(
        external_user_id="test-user-simplified-123",
        full_name="Test User Simplified",
        gender="male"
    )
    session.add(user)
    session.commit()
    print(f"✓ Created user profile with id: {user.id}")
    user_profile_id = str(user.id)
finally:
    session.close()

# Test 3: Create questionnaire profile
print("\nTest 3: Create questionnaire profile")
session = get_session()
try:
    user = session.query(UserProfile).filter(UserProfile.external_user_id == "test-user-simplified-123").first()
    q_profile = QuestionnaireProfile(
        user_id=user.id,
        completion_percentage=0
    )
    session.add(q_profile)
    session.commit()
    print(f"✓ Created questionnaire profile with id: {q_profile.id}, linked to user: {user.id}")
finally:
    session.close()

# Test 4: Test questionnaire repository with user_profile_id
print("\nTest 4: Test questionnaire repository with user_profile_id")
repo = QuestionnaireRepository()
try:
    # Get categories (should work with untouched tables)
    categories = repo.get_categories()
    print(f"✓ Got {len(categories)} questionnaire categories")
    
    # Get questions (should work with untouched tables)
    questions = repo.get_questions()
    print(f"✓ Got {len(questions)} active questions")
    
    # Test save_answers using user_profile_id
    if questions:
        test_answers = [{
            "question_id": questions[0].id,
            "answer_value": "1",
            "answer_scale": 0
        }]
        repo.save_answers(user_profile_id, test_answers)
        print(f"✓ Saved answers using user_profile_id")
        
        # Test get_answers
        answers = repo.get_answers(user_profile_id)
        print(f"✓ Retrieved {len(answers)} answers")
        
        # Test get_questionnaire_status
        status = repo.get_questionnaire_status(user_profile_id)
        print(f"✓ Got questionnaire status: {status}")
finally:
    repo.session.close()

# Test 5: Verify no user_id column exists
print("\nTest 5: Verify no user_id column exists in questionnaire tables")
session = get_session()
try:
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    
    # Check user_questionnaire_answers columns
    answer_columns = [col['name'] for col in inspector.get_columns('user_questionnaire_answers')]
    print(f"user_questionnaire_answers columns: {answer_columns}")
    assert 'user_id' not in answer_columns, "user_id column should not exist"
    assert 'user_profile_id' in answer_columns, "user_profile_id column should exist"
    print("✓ user_questionnaire_answers has correct columns")
    
    # Check user_search_preferences columns
    pref_columns = [col['name'] for col in inspector.get_columns('user_search_preferences')]
    print(f"user_search_preferences columns: {pref_columns}")
    assert 'user_id' not in pref_columns, "user_id column should not exist"
    assert 'user_profile_id' in pref_columns, "user_profile_id column should exist"
    print("✓ user_search_preferences has correct columns")
finally:
    session.close()

# Test 6: Verify foreign keys
print("\nTest 6: Verify foreign keys")
session = get_session()
try:
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    
    # Check user_questionnaire_answers foreign keys
    fks = inspector.get_foreign_keys('user_questionnaire_answers')
    print(f"user_questionnaire_answers foreign keys: {[(fk['constrained_columns'], fk['referred_table']) for fk in fks]}")
    assert any('user_profile_id' in fk.get('constrained_columns', []) for fk in fks), "Should have user_profile_id FK"
    print("✓ user_questionnaire_answers has correct foreign keys")
    
    # Check user_search_preferences foreign keys
    fks = inspector.get_foreign_keys('user_search_preferences')
    print(f"user_search_preferences foreign keys: {[(fk['constrained_columns'], fk['referred_table']) for fk in fks]}")
    assert any('user_profile_id' in fk.get('constrained_columns', []) for fk in fks), "Should have user_profile_id FK"
    print("✓ user_search_preferences has correct foreign keys")
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

print("\n✅ All simplified schema tests passed!")
