from fastapi import APIRouter, Query, Body
from sqlalchemy import func
from typing import List

from app.repositories.questionnaire_repo import QuestionnaireRepository
from app.services.questionnaire_service import QuestionnaireService
from app.schemas.recommendation import QuestionnaireAnswersSubmit
from app.services.matching.compatibility_engine import CompatibilityEngine

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
        "name": "Admin",
        "description": "Administrative questionnaire management"
    }
]

questionnaire_repo = QuestionnaireRepository()
questionnaire_service = QuestionnaireService()
matching_engine = CompatibilityEngine()




# --- MATCHING ---


@router.get("/match/property/{user_id}/{property_id}", tags=["Matching"], summary="Compute property and room compatibility scores", description="Compute property-level and room-level compatibility scores for a user. Returns property_match_score (compatibility with all occupants in the property) and rooms list with room_match_score for each room.")
async def compute_property_match(user_id: str, property_id: int):
    from fastapi import HTTPException
    
    result = await matching_engine.compute_property_and_room_scores(user_id, property_id)
    
    # Return 404 if property not found
    if "error" in result:
        raise HTTPException(status_code=404, detail=result.get("error", "Property not found"))
    
    return result


@router.post("/match/shared-properties/{user_id}", tags=["Matching"], summary="Compute property match scores for multiple properties", description="Accepts a list of property_ids from the frontend and computes compatibility scores for each property in parallel. Returns a list of property_id and property_match_score.")
async def compute_shared_properties_match(user_id: str, property_ids: List[int] = Body(...)):
    result = await matching_engine.compute_properties_match_scores(user_id, property_ids)
    return result


# --- QUESTIONNAIRE ---

@router.get("/questionnaire/questions", tags=["Questionnaire"], summary="Get all questionnaire questions", description="Return all questionnaire questions with machine keys, categories, and options map.")
def list_questions():
    return questionnaire_service.get_all_questions()


@router.post("/questionnaire/answers/{user_id}", tags=["Questionnaire"], summary="Submit questionnaire answers for a user", description="Save questionnaire answers submitted by a user. Accepts direct map of machine_key to answer_scale (no wrapper object). Returns status confirmation and answers count.")
def submit_answers(user_id: str, data: QuestionnaireAnswersSubmit):
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
    
    questionnaire_repo.save_answers(user_id, answers_list)
    return {"status": "ok", "user_id": user_id, "answers_count": len(answers_list)}


@router.get("/questionnaire/status/{user_id}", tags=["Questionnaire"], summary="Get questionnaire completion status", description="Determine whether the user completed the questionnaire by comparing answer count to total question count. Returns completed status, answered questions count, total questions, and completion percentage.")
def get_questionnaire_status(user_id: str):
    return questionnaire_repo.get_questionnaire_status(user_id)


# --- ADMIN QUESTIONNAIRE ---

@router.get("/admin/questionnaire/questions", tags=["Admin"], summary="Get all questionnaire questions (Admin)", description="Return all questionnaire questions with machine keys and options map. Administrative endpoint for questionnaire management.")
def get_all_questions_admin():
    return questionnaire_service.get_all_questions()


@router.get("/admin/questionnaire/users", tags=["Admin"], summary="Get all users with questionnaire answers", description="Return all users that currently have questionnaire answers with their answer counts.")
def get_all_users_with_answers():
    from app.database.session import get_session
    from app.database.models.user import UserQuestionnaireAnswer
    from sqlalchemy import func
    
    session = get_session()
    try:
        users = session.query(
            UserQuestionnaireAnswer.user_id,
            func.count(UserQuestionnaireAnswer.id).label("answers_count")
        ).group_by(
            UserQuestionnaireAnswer.user_id
        ).all()
        
        return [
            {
                "user_id": user.user_id,
                "answers_count": user.answers_count
            }
            for user in users
        ]
    finally:
        session.close()


@router.get("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Get user questionnaire answers (Admin)", description="View all questionnaire answers for a specific user. Returns map of machine_key to answer_scale for self-descriptive API.")
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


@router.post("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Upsert user questionnaire answers (Admin)", description="Upsert questionnaire answers for a user. Accepts direct map of machine_key to answer_scale (no wrapper object). If answer exists, it will be updated. If answer does not exist, it will be created.")
def upsert_user_answers_admin(user_id: str, data: QuestionnaireAnswersSubmit):
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


@router.delete("/admin/questionnaire/answers/{user_id}", tags=["Admin"], summary="Delete user questionnaire answers (Admin)", description="Delete all questionnaire answers for a user. This action cannot be undone.")
def delete_user_answers_admin(user_id: str):
    from app.database.session import get_session
    from app.database.models.user import UserQuestionnaireAnswer
    
    session = get_session()
    try:
        session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).delete()
        session.commit()
        return {"status": "success"}
    finally:
        session.close()
