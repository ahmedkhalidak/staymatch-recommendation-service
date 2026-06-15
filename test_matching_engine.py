"""Test matching engine with actual questionnaire data."""
import sys
import asyncio

sys.path.insert(0, '/home/ahmed-khalid/AHMED-Projects-2026/staymatch-recommendation-service')

from app.database.session import get_session
from app.database.models.user import UserQuestionnaireAnswer
from app.services.matching.compatibility_engine import CompatibilityEngine
from app.services.matching.feature_encoding import load_questionnaire_weights_and_metadata, sim, weighted_similarity
from sqlalchemy import text

print("=" * 80)
print("MATCHING ENGINE RUNTIME VERIFICATION")
print("=" * 80)

# Step 1: Load actual questionnaire data
print("\nSTEP 1: Load Questionnaire Weights and Metadata")
print("-" * 80)
weights, metadata, smoking_question_id = load_questionnaire_weights_and_metadata()
print(f"Smoking question ID: {smoking_question_id}")
print(f"Total questions with weights: {len(weights)}")
print(f"Total questions with metadata: {len(metadata)}")

# Step 2: Get actual user answers
print("\nSTEP 2: Get Actual User Answers")
print("-" * 80)
session = get_session()

# Get users with answers
users_with_answers = session.execute(text("""
    SELECT DISTINCT user_id 
    FROM user_questionnaire_answers
""")).fetchall()

user_ids = [row[0] for row in users_with_answers]
print(f"Users with answers: {user_ids}")

# Get answers for first user
test_user_id = user_ids[0]
answers = session.query(UserQuestionnaireAnswer).filter(
    UserQuestionnaireAnswer.user_id == test_user_id
).all()

print(f"\nUser: {test_user_id}")
print(f"Total answers: {len(answers)}")
print("\nAnswer details:")
for ans in answers:
    print(f"  Question {ans.question_id}: answer_scale={ans.answer_scale}, answer_value={ans.answer_value}")

# Convert to dict format
answers_dict = {str(ans.question_id): ans.answer_scale for ans in answers}
print(f"\nAnswers dict: {answers_dict}")

# Step 3: Test similarity calculation
print("\nSTEP 3: Test Similarity Calculation")
print("-" * 80)

# Get second user for comparison
if len(user_ids) > 1:
    test_user_id_2 = user_ids[1]
    answers_2 = session.query(UserQuestionnaireAnswer).filter(
        UserQuestionnaireAnswer.user_id == test_user_id_2
    ).all()
    answers_dict_2 = {str(ans.question_id): ans.answer_scale for ans in answers_2}
    
    print(f"Comparing user {test_user_id} with user {test_user_id_2}")
    print(f"User 1 answers: {answers_dict}")
    print(f"User 2 answers: {answers_dict_2}")
    
    # Calculate weighted similarity
    similarity = weighted_similarity(
        answers_dict,
        answers_dict_2,
        weights,
        metadata,
        smoking_question_id
    )
    print(f"\nWeighted similarity score: {similarity}")
    
    # Show individual question similarities
    print("\nIndividual question similarities:")
    shared_questions = set(answers_dict.keys()) & set(answers_dict_2.keys())
    for qid_str in shared_questions:
        qid = int(qid_str)
        s = sim(qid, answers_dict[qid_str], answers_dict_2[qid_str], metadata, smoking_question_id)
        w = weights.get(qid, 0)
        print(f"  Question {qid}: similarity={s:.4f}, weight={w}, contribution={s*w:.4f}")
else:
    print("Only one user with answers - cannot test pairwise comparison")

# Step 4: Test Compatibility Engine initialization
print("\nSTEP 4: Test Compatibility Engine Initialization")
print("-" * 80)
try:
    engine = CompatibilityEngine()
    print("✓ CompatibilityEngine initialized successfully")
    print(f"  Smoking question ID: {engine.smoking_question_id}")
    print(f"  Age question ID: {engine.age_question_id}")
    print(f"  Occupation question ID: {engine.occupation_question_id}")
except Exception as e:
    print(f"✗ CompatibilityEngine initialization failed: {e}")

# Step 5: Test _compute_pairwise function
print("\nSTEP 5: Test _compute_pairwise Function")
print("-" * 80)
if len(user_ids) > 1:
    try:
        # Get profiles for both users
        profile_1 = session.execute(text(f"""
            SELECT * FROM user_profiles WHERE external_user_id = '{test_user_id}'
        """)).fetchone()
        
        profile_2 = session.execute(text(f"""
            SELECT * FROM user_profiles WHERE external_user_id = '{test_user_id_2}'
        """)).fetchone()
        
        print(f"User 1 profile: {profile_1}")
        print(f"User 2 profile: {profile_2}")
        
        # Convert to dict format
        profile_dict_1 = {
            "gender": profile_1[4] if profile_1 else None,
            "birth_year": profile_1[5] if profile_1 else None,
            "occupation": profile_1[7] if profile_1 else None,
        }
        profile_dict_2 = {
            "gender": profile_2[4] if profile_2 else None,
            "birth_year": profile_2[5] if profile_2 else None,
            "occupation": profile_2[7] if profile_2 else None,
        }
        
        pairwise_score = engine._compute_pairwise(
            answers_dict,
            answers_dict_2,
            profile_dict_1,
            profile_dict_2
        )
        
        print(f"\nPairwise score: {pairwise_score}")
        
        # Show the formula breakdown
        q_score = weighted_similarity(
            {k: v for k, v in answers_dict.items() if int(k) not in [engine.age_question_id, engine.occupation_question_id]},
            {k: v for k, v in answers_dict_2.items() if int(k) not in [engine.age_question_id, engine.occupation_question_id]},
            {k: v for k, v in weights.items() if k not in [engine.age_question_id, engine.occupation_question_id]},
            metadata,
            smoking_question_id
        )
        
        # Occupation similarity
        occ_sim = 1.0
        if profile_dict_1.get("occupation") and profile_dict_2.get("occupation"):
            occ_sim = 1.0 if profile_dict_1["occupation"] == profile_dict_2["occupation"] else 0.5
        
        # Age similarity
        age_sim = 1.0
        if profile_dict_1.get("birth_year") and profile_dict_2.get("birth_year"):
            age_diff = abs(profile_dict_1["birth_year"] - profile_dict_2["birth_year"])
            age_sim = max(0.0, 1.0 - age_diff / 20.0)
        
        print(f"\nFormula breakdown:")
        print(f"  Questionnaire similarity (85%): {q_score:.4f}")
        print(f"  Occupation similarity (8%): {occ_sim:.4f}")
        print(f"  Age similarity (7%): {age_sim:.4f}")
        print(f"  Final: 0.85 * {q_score:.4f} + 0.08 * {occ_sim:.4f} + 0.07 * {age_sim:.4f} = {pairwise_score:.4f}")
        
    except Exception as e:
        print(f"✗ _compute_pairwise failed: {e}")
        import traceback
        traceback.print_exc()

session.close()

print("\n" + "=" * 80)
print("MATCHING ENGINE RUNTIME VERIFICATION COMPLETE")
print("=" * 80)
