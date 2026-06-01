from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.repositories.property_repo import PropertyRepository, RoomRepository
from app.repositories.property_repo import QuestionnaireRepository, SearchPreferenceRepository, RecommendationRepository
from app.repositories.property_repo import UserRepository, InteractionRepository
from app.services.scoring.budget_scorer import BudgetScorer
from app.services.scoring.location_scorer import LocationScorer
from app.services.scoring.amenity_scorer import AmenityScorer
from app.services.scoring.tenant_scorer import TenantScorer
from app.services.recommendation.property_recommender import PropertyRecommender, RoomRecommender
from app.services.sync.data_sync import DataSyncService
from app.services.questionnaire_service import QuestionnaireService
from app.schemas.recommendation import (
    UserProfileCreate, SearchPreferenceCreate, QuestionnaireAnswersSubmit,
    InteractionCreate, MatchComputeResponse, MatchResultResponse
)

router = APIRouter()
property_repo = PropertyRepository()
room_repo = RoomRepository()
user_repo = UserRepository()
questionnaire_repo = QuestionnaireRepository()
pref_repo = SearchPreferenceRepository()
rec_repo = RecommendationRepository()
interaction_repo = InteractionRepository()
property_recommender = PropertyRecommender()
room_recommender = RoomRecommender()
questionnaire_service = QuestionnaireService()


# --- SYNC ---

@router.post("/sync/refresh")
def trigger_sync():
    service = DataSyncService()
    results = service.sync_all()
    return {"status": "ok", "results": results}


@router.get("/sync/status")
def sync_status():
    return {"status": "ok", "message": "Sync status endpoint"}


# --- RECOMMENDATIONS ---

@router.get("/recommend/properties/{user_id}")
def get_property_recommendations(user_id: str):
    properties = property_repo.get_all_approved()
    user = user_repo.get_profile(user_id)
    prefs = pref_repo.get(user_id)
    answers = questionnaire_repo.get_answers(user_id)

    context = {
        "preferences": prefs,
        "questionnaire_answers": [{"question_id": a.question_id, "answer_value": a.answer_value} for a in (answers or [])],
    }
    if prefs:
        context["max_budget"] = prefs.max_budget
        context["min_budget"] = prefs.min_budget
        context["preferred_city"] = prefs.preferred_city
        context["preferred_government"] = prefs.preferred_government

    scored = property_recommender.recommend(user or prefs, properties, context)
    rec_repo.save_property_recommendations(user_id, scored)

    return {
        "user_id": user_id,
        "recommendations": [
            {"property_id": p.id, "score": s, "score_breakdown": b, "rank": i}
            for i, (p, s, b) in enumerate(scored)
        ]
    }


@router.get("/recommend/rooms/{user_id}")
def get_room_recommendations(user_id: str):
    rooms = room_repo.get_available()
    user = user_repo.get_profile(user_id)
    prefs = pref_repo.get(user_id)

    context = {"preferences": prefs}
    if prefs:
        context["max_budget"] = prefs.max_budget
        context["min_budget"] = prefs.min_budget
        context["preferred_city"] = prefs.preferred_city
        context["preferred_government"] = prefs.preferred_government

    scored = room_recommender.recommend(user or prefs, rooms, context)
    rec_repo.save_room_recommendations(user_id, scored)

    return {
        "user_id": user_id,
        "recommendations": [
            {"room_id": r.id, "property_id": getattr(p, "id", None), "score": s, "score_breakdown": b, "rank": i}
            for i, (r, s, b, p) in enumerate(scored)
        ]
    }


@router.post("/recommend/compute/{user_id}")
def compute_recommendations(user_id: str):
    return get_property_recommendations(user_id)


# --- MATCHING ---

@router.post("/match/compute/{user_id}")
def compute_matches(user_id: str):
    return {"status": "computed", "seeker_user_id": user_id, "matches": []}


@router.get("/match/results/{user_id}")
def get_match_results(user_id: str):
    from app.repositories.property_repo import MatchingRepository
    match_repo = MatchingRepository()
    matches = match_repo.get_matches(user_id)
    return {
        "seeker_user_id": user_id,
        "results": [
            {
                "room_id": m.room_id,
                "property_id": m.property_id,
                "room_compatibility_score": m.room_compatibility_score,
                "created_at": m.created_at,
            }
            for m in matches
        ]
    }


# --- USERS ---

@router.post("/users/profile")
def create_or_update_profile(data: UserProfileCreate):
    profile = user_repo.upsert_profile(data.user_id, data.model_dump(exclude={"user_id"}))
    return {"status": "ok", "user_id": data.user_id}


@router.get("/users/profile/{user_id}")
def get_profile(user_id: str):
    profile = user_repo.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": str(profile.id),
        "external_user_id": profile.external_user_id,
        "full_name": profile.full_name,
        "phone": profile.phone,
        "gender": profile.gender,
        "birth_year": profile.birth_year,
        "nationality": profile.nationality,
        "occupation": profile.occupation,
        "created_at": profile.created_at,
    }


@router.post("/users/preferences")
def save_preferences(data: SearchPreferenceCreate):
    pref = pref_repo.upsert(data.user_id, data.model_dump(exclude={"user_id"}))
    return {"status": "ok", "user_id": data.user_id}


@router.get("/users/preferences/{user_id}")
def get_preferences(user_id: str):
    pref = pref_repo.get(user_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return {
        "user_id": pref.user_id,
        "min_budget": pref.min_budget,
        "max_budget": pref.max_budget,
        "preferred_city": pref.preferred_city,
        "preferred_government": pref.preferred_government,
        "preferred_property_type": pref.preferred_property_type,
        "furnished": pref.furnished,
        "wifi": pref.wifi,
        "air_conditioning": pref.air_conditioning,
        "balcony": pref.balcony,
        "private_bathroom": pref.private_bathroom,
        "tenant_type": pref.tenant_type,
        "gender_preference": pref.gender_preference,
        "shared_room": pref.shared_room,
    }


# --- QUESTIONNAIRE ---

@router.get("/questionnaire/questions")
def list_questions():
    return questionnaire_service.get_all_questions()


@router.post("/questionnaire/answers/{user_id}")
def submit_answers(user_id: str, data: QuestionnaireAnswersSubmit):
    answers = [a.model_dump() for a in data.answers]
    questionnaire_repo.save_answers(user_id, answers)
    return {"status": "ok", "user_id": user_id, "answers_count": len(answers)}


@router.get("/questionnaire/answers/{user_id}")
def get_answers(user_id: str):
    answers = questionnaire_repo.get_answers(user_id)
    return {
        "user_id": user_id,
        "answers": [
            {
                "question_id": a.question_id,
                "answer_value": a.answer_value,
                "answer_scale": a.answer_scale,
                "answered_at": a.answered_at,
            }
            for a in answers
        ]
    }


# --- INTERACTIONS ---

@router.post("/interactions")
def log_interaction(data: InteractionCreate):
    interaction_repo.log(data.model_dump())
    return {"status": "ok"}


@router.get("/interactions/{user_id}")
def get_interactions(user_id: str):
    interactions = interaction_repo.get_by_user(user_id)
    return {
        "user_id": user_id,
        "interactions": [
            {
                "id": i.id,
                "target_type": i.target_type,
                "target_id": i.target_id,
                "action": i.action,
                "context": i.context,
                "created_at": i.created_at,
            }
            for i in interactions
        ]
    }