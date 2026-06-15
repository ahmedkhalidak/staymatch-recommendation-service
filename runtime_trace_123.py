#!/usr/bin/env python3
"""Runtime trace for property 123 scoring."""

import asyncio
from app.services.matching.compatibility_engine import CompatibilityEngine
from app.services.matching.feature_encoding import load_questionnaire_weights_and_metadata, sim
from app.database.session import get_session
from app.database.models.user import UserQuestionnaireAnswer


async def runtime_trace():
    """Execute runtime trace for property 123."""
    seeker_id = "3ee32cef-cdbe-4a63-94a1-819e34a88fec"
    property_id = 123
    
    print("=" * 80)
    print("RUNTIME TRACE FOR PROPERTY 123")
    print("=" * 80)
    
    # Load questionnaire weights and metadata
    print("\n" + "=" * 80)
    print("LOADING QUESTIONNAIRE WEIGHTS AND METADATA")
    print("=" * 80)
    
    weights, metadata, smoking_question_id = load_questionnaire_weights_and_metadata()
    
    print(f"\nTotal weights loaded: {len(weights)}")
    print(f"Total metadata loaded: {len(metadata)}")
    print(f"Smoking question ID: {smoking_question_id}")
    
    print("\nWeights:")
    for qid, w in sorted(weights.items()):
        print(f"  Question {qid}: {w}")
    
    print("\nMetadata sample (first 5):")
    for i, (qid, meta) in enumerate(sorted(metadata.items())):
        if i >= 5:
            break
        print(f"  Question {qid}: {meta}")
    
    # Initialize engine
    print("\n" + "=" * 80)
    print("INITIALIZING COMPATIBILITY ENGINE")
    print("=" * 80)
    
    engine = CompatibilityEngine()
    
    print(f"\nEngine age_question_id: {engine.age_question_id}")
    print(f"Engine occupation_question_id: {engine.occupation_question_id}")
    print(f"Engine smoking_question_id: {engine.smoking_question_id}")
    
    # Get seeker answers
    print("\n" + "=" * 80)
    print("SEEKER ANSWERS")
    print("=" * 80)
    
    seeker_answers = engine._get_answers_as_dict(seeker_id)
    print(f"\nSeeker has {len(seeker_answers)} answers")
    for qid, val in sorted(seeker_answers.items(), key=lambda x: int(x[0])):
        print(f"  Question {qid}: {val}")
    
    # Get seeker profile
    print("\n" + "=" * 80)
    print("SEEKER PROFILE")
    print("=" * 80)
    
    seeker_profile = await engine._get_user_profile_from_api(seeker_id)
    print(f"\nSeeker profile: {seeker_profile}")
    
    # Get property occupants
    print("\n" + "=" * 80)
    print("PROPERTY 123 OCCUPANTS")
    print("=" * 80)
    
    from app.services.property_api_client import get_property_api_client
    api_client = get_property_api_client()
    
    property_occupants = await api_client.get_property_occupants(property_id)
    print(f"\nProperty 123 has {len(property_occupants)} occupants")
    
    for occ in property_occupants:
        user_id = occ.get("userId")
        print(f"\n  Occupant: {user_id}")
        
        # Get occupant answers
        occupant_answers = engine._get_answers_as_dict(user_id)
        print(f"    Answers: {len(occupant_answers)} questions")
        
        # Get occupant profile
        occupant_profile = await engine._get_user_profile_from_api(user_id)
        print(f"    Profile: {occupant_profile}")
        
        # Compute pairwise score
        print(f"\n    Computing pairwise score...")
        
        # Filter out age and occupation questions
        filtered_answers_a = {k: v for k, v in seeker_answers.items() if int(k) not in [engine.age_question_id, engine.occupation_question_id]}
        filtered_answers_b = {k: v for k, v in occupant_answers.items() if int(k) not in [engine.age_question_id, engine.occupation_question_id]}
        
        # Also filter weights
        filtered_weights = {k: v for k, v in engine.weights.items() if k not in [engine.age_question_id, engine.occupation_question_id]}
        
        print(f"    Filtered seeker answers: {len(filtered_answers_a)}")
        print(f"    Filtered occupant answers: {len(filtered_answers_b)}")
        print(f"    Filtered weights: {len(filtered_weights)}")
        
        # Calculate questionnaire score
        total_w = 0.0
        total_sim = 0.0
        smoke_penalty = 1.0
        
        print(f"\n    Per-question similarity:")
        for qid_str in sorted(filtered_answers_a.keys(), key=lambda x: int(x)):
            qid = int(qid_str)
            if qid not in filtered_answers_b:
                continue
            
            w = filtered_weights.get(qid, 0.0)
            if w <= 0:
                continue
            
            a = filtered_answers_a[qid_str]
            b = filtered_answers_b[qid_str]
            
            s = sim(qid, a, b, engine.question_metadata, engine.smoking_question_id)
            
            if qid == engine.smoking_question_id and s < 0.5:
                smoke_penalty = 0.3
            
            total_sim += w * s
            total_w += w
            
            meta = engine.question_metadata.get(qid, {})
            question_type = meta.get("question_type", "unknown")
            
            print(f"      Q{qid} (w={w}, type={question_type}): a={a}, b={b}, sim={s}, contrib={w*s}")
        
        q_score = (total_sim / total_w) * smoke_penalty if total_w > 0 else 0.5
        
        print(f"\n    Questionnaire score: {q_score}")
        print(f"    Total weighted similarity: {total_sim}")
        print(f"    Total weight: {total_w}")
        print(f"    Smoke penalty: {smoke_penalty}")
        
        # Calculate occupation similarity
        occupation_sim = 1.0
        if seeker_profile and occupant_profile and seeker_profile.get("occupation") and occupant_profile.get("occupation"):
            occ_a = seeker_profile.get("occupation", "").lower() if seeker_profile.get("occupation") else ""
            occ_b = occupant_profile.get("occupation", "").lower() if occupant_profile.get("occupation") else ""
            occupation_sim = 1.0 if occ_a == occ_b else 0.5
        
        print(f"    Occupation similarity: {occupation_sim}")
        
        # Calculate age similarity
        age_sim = 1.0
        if seeker_profile and occupant_profile and seeker_profile.get("birth_year") and occupant_profile.get("birth_year"):
            age_diff = abs(seeker_profile.get("birth_year") - occupant_profile.get("birth_year"))
            age_sim = max(0.0, 1.0 - age_diff / 20.0)
        
        print(f"    Age similarity: {age_sim}")
        
        # Final pairwise score
        final_pairwise = 0.85 * q_score + 0.08 * occupation_sim + 0.07 * age_sim
        
        print(f"\n    Final pairwise score: 0.85 * {q_score} + 0.08 * {occupation_sim} + 0.07 * {age_sim} = {final_pairwise}")
        print(f"    Threshold check: {final_pairwise} >= 0.3 = {final_pairwise >= 0.3}")
    
    # Compute actual property score
    print("\n" + "=" * 80)
    print("ACTUAL PROPERTY SCORE")
    print("=" * 80)
    
    result = await engine.compute_property_and_room_scores(seeker_id, property_id)
    
    print(f"\nProperty {property_id} result:")
    print(f"  Property match score: {result.get('property_match_score')}")
    print(f"  Rooms: {len(result.get('rooms', []))}")
    
    for room in result.get('rooms', []):
        print(f"  Room {room['room_id']}: {room['room_match_score']} (occupants: {room['occupants_count']})")


if __name__ == "__main__":
    asyncio.run(runtime_trace())
