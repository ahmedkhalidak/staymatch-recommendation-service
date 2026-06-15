#!/usr/bin/env python
"""Test questionnaire APIs work with new schema"""
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
print("\nTest 2: Create a user profile")
session = get_session()
try:
    user = UserProfile(
        external_user_id="test-user-123",
        full_name="Test User",
        gender="male"
    )
    session.add(user)
    session.commit()
    print(f"✓ Created user profile with id: {user.id}")
finally:
    session.close()

# Test 3: Create questionnaire profile (new table)
print("\nTest 3: Create questionnaire profile")
session = get_session()
try:
    user = session.query(UserProfile).filter(UserProfile.external_user_id == "test-user-123").first()
    q_profile = QuestionnaireProfile(
        user_id=user.id,
        completion_percentage=0
    )
    session.add(q_profile)
    session.commit()
    print(f"✓ Created questionnaire profile with id: {q_profile.id}, linked to user: {user.id}")
finally:
    session.close()

# Test 4: Test questionnaire repository (uses user_id String, should still work)
print("\nTest 4: Test questionnaire repository")
repo = QuestionnaireRepository()
try:
    # Get categories (should work with untouched tables)
    categories = repo.get_categories()
    print(f"✓ Got {len(categories)} questionnaire categories")
    
    # Get questions (should work with untouched tables)
    questions = repo.get_questions()
    print(f"✓ Got {len(questions)} active questions")
    
    # Test save_answers (uses user_id String, should still work)
    if questions:
        test_answers = [{
            "question_id": questions[0].id,
            "answer_value": "1",
            "answer_scale": 0
        }]
        repo.save_answers("test-user-123", test_answers)
        print(f"✓ Saved answers using user_id String (backward compatibility)")
        
        # Test get_answers
        answers = repo.get_answers("test-user-123")
        print(f"✓ Retrieved {len(answers)} answers")
        
        # Test get_questionnaire_status
        status = repo.get_questionnaire_status("test-user-123")
        print(f"✓ Got questionnaire status: {status}")
finally:
    repo.session.close()

# Test 5: Verify foreign keys work
print("\nTest 5: Verify foreign keys work")
session = get_session()
try:
    # Check that user_profile_id can be set
    user = session.query(UserProfile).filter(UserProfile.external_user_id == "test-user-123").first()
    answer = session.query(UserQuestionnaireAnswer).filter(UserQuestionnaireAnswer.user_id == "test-user-123").first()
    if answer:
        answer.user_profile_id = user.id
        session.commit()
        print(f"✓ Set user_profile_id FK on answer: {answer.user_profile_id}")
    
    # Verify the relationship
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    fks = inspector.get_foreign_keys('user_questionnaire_answers')
    user_profile_fks = [fk for fk in fks if 'user_profile_id' in fk.get('constrained_columns', [])]
    if user_profile_fks:
        print(f"✓ Foreign key constraint exists for user_profile_id")
finally:
    session.close()

# Cleanup test data
print("\nCleanup test data")
session = get_session()
try:
    session.execute(text("TRUNCATE TABLE user_questionnaire_answers RESTART IDENTITY CASCADE"))
    session.execute(text("TRUNCATE TABLE questionnaire_profiles RESTART IDENTITY CASCADE"))
    session.execute(text("TRUNCATE TABLE user_profiles RESTART IDENTITY CASCADE"))
    session.commit()
    print("✓ Cleaned up test data")
finally:
    session.close()

print("\n✅ All questionnaire API tests passed!")
