from fastapi import APIRouter, Query, Body, Depends
from sqlalchemy import func
from typing import List

from app.repositories.questionnaire_repo import QuestionnaireRepository
from app.services.questionnaire_service import QuestionnaireService
from app.schemas.recommendation import (
    QuestionnaireAnswersSubmit,
    QuestionnaireQuestionsResponse,
    QuestionnaireStatusResponse,
    QuestionnaireAnswersSubmitResponse,
    PropertyMatchResponse,
    SharedPropertiesMatchResponse,
    AdminUsersListResponse,
    AdminUserAnswersResponse,
    AdminUpsertResponse
)
from app.schemas.profile import ProfileQuestionnaireResponse
from app.core.schemas import ErrorResponse
from app.services.matching.compatibility_engine import CompatibilityEngine
from app.services.profile_questionnaire_service import ProfileQuestionnaireService
from app.core.security import get_current_user, CurrentUser

router = APIRouter()

# Tags for Swagger documentation
tags_metadata = [
    {
        "name": "Matching",
        "description": "Roommate and property compatibility scoring using .NET API data"
    },
    {
        "name": "Questionnaire",
        "description": "Questionnaire questions, answers, and completion status management"
    },
    {
        "name": "Profile",
        "description": "User profile questionnaire data for Profile UI"
    },
    {
        "name": "Admin",
        "description": "Administrative questionnaire management"
    }
]

questionnaire_repo = QuestionnaireRepository()
questionnaire_service = QuestionnaireService()
matching_engine = CompatibilityEngine()
profile_questionnaire_service = ProfileQuestionnaireService()




# --- MATCHING ---


@router.get("/match/property/{property_id}", tags=["Matching"], summary="Compute property and room compatibility scores", description="Compute property-level and room-level compatibility scores for a user. Returns property_match_score (compatibility with all occupants in the property) and rooms list with room_match_score for each room.", response_model=PropertyMatchResponse, responses={
    200: {
        "description": "Property and room compatibility scores computed successfully",
        "content": {
            "application/json": {
                "example": {
                    "property_id": 456,
                    "property_match_score": 78.2,
                    "rooms": [
                        {"room_id": 123, "room_match_score": 85.5},
                        {"room_id": 124, "room_match_score": 72.3}
                    ]
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    404: {
        "description": "Property not found",
        "content": {
            "application/json": {
                "example": {"error": "not_found", "message": "Property not found"}
            }
        }
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Invalid request parameters", "details": {"field": "property_id", "reason": "Must be a valid integer"}}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
async def compute_property_match(current_user: CurrentUser = Depends(get_current_user), property_id: int = None):
    from fastapi import HTTPException
    
    result = await matching_engine.compute_property_and_room_scores(current_user.user_id, property_id, token=current_user.token)
    
    # Return 404 if property not found
    if "error" in result:
        raise HTTPException(status_code=404, detail=result.get("error", "Property not found"))
    
    return result


@router.post("/match/shared-properties", tags=["Matching"], summary="Compute property match scores for multiple properties", description="Accepts a list of property_ids from the frontend and computes compatibility scores for each property in parallel. Returns a list of property_id and property_match_score.", response_model=SharedPropertiesMatchResponse, responses={
    200: {
        "description": "Property match scores computed successfully",
        "content": {
            "application/json": {
                "example": {
                    "matches": [
                        {"property_id": 456, "property_match_score": 78.2},
                        {"property_id": 457, "property_match_score": 65.4},
                        {"property_id": 458, "property_match_score": 82.1}
                    ]
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Invalid request body", "details": {"field": "property_ids", "reason": "Must be a non-empty list of integers"}}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
async def compute_shared_properties_match(current_user: CurrentUser = Depends(get_current_user), property_ids: List[int] = Body(..., description="List of property IDs to compute match scores for", example=[456, 457, 458])):
    result = await matching_engine.compute_properties_match_scores(current_user.user_id, property_ids, token=current_user.token)
    return result


# --- QUESTIONNAIRE ---

@router.get("/questionnaire/questions", tags=["Questionnaire"], summary="Get all questionnaire questions", description="Return all questionnaire questions with machine keys, categories, and options map.", response_model=QuestionnaireQuestionsResponse, responses={
    200: {
        "description": "Questionnaire questions retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "questions": [
                        {
                            "id": 1,
                            "machine_key": "age_group",
                            "question_text": "What is your age group?",
                            "category": "demographics",
                            "options": {
                                "option_1": {"value": 1, "label": "18-24"},
                                "option_2": {"value": 2, "label": "25-34"},
                                "option_3": {"value": 3, "label": "35-44"},
                                "option_4": {"value": 4, "label": "45+"}
                            }
                        }
                    ]
                }
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def list_questions():
    return {"questions": questionnaire_service.get_all_questions()}


@router.post("/questionnaire/answers", tags=["Questionnaire"], summary="Submit questionnaire answers for a user", description="Save questionnaire answers submitted by a user. Accepts direct map of machine_key to answer_scale (no wrapper object). Returns status confirmation and answers count.", response_model=QuestionnaireAnswersSubmitResponse, responses={
    200: {
        "description": "Questionnaire answers submitted successfully",
        "content": {
            "application/json": {
                "example": {
                    "status": "ok",
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answers_count": 13
                }
            }
        }
    },
    400: {
        "description": "Invalid answers - validation failed",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Answer value out of range for question age_group"}
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Invalid request body", "details": {"field": "age_group", "reason": "Value must be between 1 and 4"}}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
async def submit_answers(current_user: CurrentUser = Depends(get_current_user), data: QuestionnaireAnswersSubmit = Body(..., description="Questionnaire answers as key-value pairs")):
    # Convert Pydantic model to dict of non-null values
    answers_dict = data.model_dump(exclude_none=True)
    
    # Validate answers against option counts
    try:
        questionnaire_service.validate_answers_against_options(answers_dict)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    
    # Transform from machine_key to question_id format
    transformed_answers = questionnaire_service.transform_answers_from_map(answers_dict)
    
    # Convert to list format expected by repository
    answers_list = [
        {
            "question_id": int(qid),
            "answer_value": str(scale),  # Store as string for compatibility
            "answer_scale": scale - 1  # Convert 1-based to 0-based for storage
        }
        for qid, scale in transformed_answers.items()
    ]
    
    questionnaire_repo.save_answers(current_user.user_id, answers_list)
    return {"status": "ok", "user_id": current_user.user_id, "answers_count": len(answers_list)}


@router.get("/questionnaire/status", tags=["Questionnaire"], summary="Get questionnaire completion status", description="Determine whether the user completed the questionnaire by comparing answer count to total question count. Returns completed status, answered questions count, total questions, and completion percentage.", response_model=QuestionnaireStatusResponse, responses={
    200: {
        "description": "Questionnaire status retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answered_questions": 5,
                    "total_questions": 13,
                    "completed": False,
                    "completion_percentage": 38,
                    "missing_question_ids": [6, 7, 8, 9, 10, 11, 12, 13],
                    "next_question_id": 6
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    404: {
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {"error": "not_found", "message": "User profile not found"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
async def get_questionnaire_status(current_user: CurrentUser = Depends(get_current_user)):
    return questionnaire_repo.get_questionnaire_status(current_user.user_id)


# --- PROFILE ---


@router.get("/profile/questionnaire", tags=["Profile"], summary="Get profile questionnaire data", description="Get complete profile questionnaire data for the Profile UI. Returns completion status, compatibility preferences, housing preferences, vibe check, and about me text.", response_model=ProfileQuestionnaireResponse, responses={
    200: {
        "description": "Profile questionnaire data retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "completed": True,
                    "can_match": True,
                    "can_edit": True,
                    "needs_questionnaire": False,
                    "answered_questions": 13,
                    "total_questions": 13,
                    "completion_percentage": 100,
                    "missing_question_ids": [],
                    "next_question_id": None,
                    "last_updated": "2024-01-15T10:30:00Z",
                    "about_me": "Software engineer who enjoys hiking and coffee",
                    "compatibility_preferences": {
                        "smoker": False,
                        "has_pets": None,
                        "night_owl": True
                    },
                    "housing_preferences": {
                        "governorate": "Capital",
                        "budget": 450
                    },
                    "vibe_check": {
                        "cleanliness_level": {"value": 3, "label": "Moderate"},
                        "cultural_importance": {"value": 2, "label": "Somewhat important"}
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    404: {
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {"error": "not_found", "message": "User profile not found"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
async def get_profile_questionnaire(current_user: CurrentUser = Depends(get_current_user)):
    return await profile_questionnaire_service.get_profile_questionnaire(current_user.user_id)


# --- ADMIN QUESTIONNAIRE ---

@router.get("/admin/questionnaire/questions", tags=["Admin"], summary="Get all questionnaire questions (Admin)", description="Return all questionnaire questions with machine keys and options map. Administrative endpoint for questionnaire management.", response_model=QuestionnaireQuestionsResponse, responses={
    200: {
        "description": "Questionnaire questions retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "questions": [
                        {
                            "id": 1,
                            "machine_key": "age_group",
                            "question_text": "What is your age group?",
                            "category": "demographics",
                            "options": {
                                "option_1": {"value": 1, "label": "18-24"},
                                "option_2": {"value": 2, "label": "25-34"},
                                "option_3": {"value": 3, "label": "35-44"},
                                "option_4": {"value": 4, "label": "45+"}
                            }
                        }
                    ]
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def get_all_questions_admin():
    return {"questions": questionnaire_service.get_all_questions()}


@router.get("/admin/questionnaire/users", tags=["Admin"], summary="Get all users with questionnaire answers", description="Return all users that currently have questionnaire answers with their answer counts.", response_model=AdminUsersListResponse, responses={
    200: {
        "description": "Users with questionnaire answers retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "users": [
                        {
                            "user_profile_id": 1,
                            "external_user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                            "answers_count": 13
                        },
                        {
                            "user_profile_id": 2,
                            "external_user_id": "74b1d1f0-2bb3-526c-92d6-3449fb9gc660",
                            "answers_count": 8
                        }
                    ]
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def get_all_users_with_answers():
    from app.database.session import get_session
    from app.database.models.user import UserQuestionnaireAnswer, UserProfile
    from sqlalchemy import func
    
    session = get_session()
    try:
        users = session.query(
            UserQuestionnaireAnswer.user_profile_id,
            UserProfile.external_user_id,
            func.count(UserQuestionnaireAnswer.id).label("answers_count")
        ).join(
            UserProfile, UserQuestionnaireAnswer.user_profile_id == UserProfile.id
        ).group_by(
            UserQuestionnaireAnswer.user_profile_id,
            UserProfile.external_user_id
        ).all()
        
        return [
            {
                "user_profile_id": user.user_profile_id,
                "external_user_id": user.external_user_id,
                "answers_count": user.answers_count
            }
            for user in users
        ]
    finally:
        session.close()


@router.get("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Get user questionnaire answers (Admin)", description="View all questionnaire answers for a specific user. Returns map of machine_key to answer_scale for self-descriptive API.", response_model=AdminUserAnswersResponse, responses={
    200: {
        "description": "User questionnaire answers retrieved successfully",
        "content": {
            "application/json": {
                "example": {
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answers": {
                        "age_group": 2,
                        "occupation_status": 1,
                        "study_or_work_field": 3,
                        "busiest_time": 2,
                        "sleep_time": 3,
                        "first_activity_home": 2,
                        "mess_tolerance": 3,
                        "free_day_style": 2,
                        "group_activity_preference": 3,
                        "study_environment": 2,
                        "smoking_preference": 1,
                        "biggest_shared_living_issue": 2,
                        "flexibility_level": 3
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    404: {
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {"error": "not_found", "message": "User profile not found"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def get_user_answers_admin(user_id: str):
    answers = questionnaire_repo.get_answers(user_id)
    
    # Convert to question_id -> answer_scale map
    answers_dict = {str(a.question_id): a.answer_scale for a in answers}
    
    # Transform to machine_key -> answer_scale map
    transformed = questionnaire_service.transform_answers_to_map(answers_dict)
    
    return {
        "user_id": user_id,
        "answers": transformed
    }


@router.post("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Upsert user questionnaire answers (Admin)", description="Upsert questionnaire answers for a user. Accepts direct map of machine_key to answer_scale (no wrapper object). If answer exists, it will be updated. If answer does not exist, it will be created.", response_model=AdminUpsertResponse, responses={
    200: {
        "description": "User questionnaire answers upserted successfully",
        "content": {
            "application/json": {
                "example": {"status": "success"}
            }
        }
    },
    400: {
        "description": "Invalid answers - validation failed",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Answer value out of range for question age_group"}
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {"error": "validation_error", "message": "Invalid request body", "details": {"field": "age_group", "reason": "Value must be between 1 and 4"}}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def upsert_user_answers_admin(user_id: str, data: QuestionnaireAnswersSubmit = Body(..., description="Questionnaire answers as key-value pairs")):
    # Convert Pydantic model to dict of non-null values
    answers_dict = data.model_dump(exclude_none=True)
    
    # Validate answers against option counts
    try:
        questionnaire_service.validate_answers_against_options(answers_dict)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    
    # Transform from machine_key to question_id format
    transformed_answers = questionnaire_service.transform_answers_from_map(answers_dict)
    
    # Convert to list format expected by repository
    answers_list = [
        {
            "question_id": int(qid),
            "answer_value": str(scale),
            "answer_scale": scale - 1  # Convert 1-based to 0-based for storage
        }
        for qid, scale in transformed_answers.items()
    ]
    
    questionnaire_repo.save_answers(user_id, answers_list)
    return {"status": "success"}


@router.delete("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Delete user questionnaire answers (Admin)", description="Delete all questionnaire answers for a user. This action cannot be undone.", response_model=AdminUpsertResponse, responses={
    200: {
        "description": "User questionnaire answers deleted successfully",
        "content": {
            "application/json": {
                "example": {"status": "success"}
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "Authentication required"}
            }
        }
    },
    404: {
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {"error": "not_found", "message": "User profile not found"}
            }
        }
    },
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {"error": "internal_error", "message": "Unexpected server error"}
            }
        }
    }
})
def delete_user_answers_admin(user_id: str):
    from app.database.session import get_session
    from app.database.models.user import UserQuestionnaireAnswer, UserProfile
    
    session = get_session()
    try:
        # Resolve external user_id to user_profile_id
        user_profile = session.query(UserProfile).filter(UserProfile.external_user_id == user_id).first()
        if not user_profile:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")
        
        session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_profile_id == user_profile.id
        ).delete()
        session.commit()
        return {"status": "success"}
    finally:
        session.close()
