from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi import BackgroundTasks
from sqlalchemy import func

from app.repositories.property_repo import (
    PropertyRepository, RoomRepository, QuestionnaireRepository,
    SearchPreferenceRepository, RecommendationRepository,
    UserRepository, InteractionRepository, MatchingRepository
)
from app.services.recommendation.property_recommender import PropertyRecommender, RoomRecommender
from app.services.sync.data_sync import DataSyncService
from app.services.questionnaire_service import QuestionnaireService
from app.schemas.recommendation import (
    UserProfileCreate, SearchPreferenceCreate, QuestionnaireAnswersSubmit,
    InteractionCreate
)
from app.core.security import verify_api_key
from app.services.interaction_analyzer import InteractionAnalyzer, UserClassifier
from app.services.matching.compatibility_engine import CompatibilityEngine
from app.services.scoring.feedback_scorer import FeedbackScorer
from app.repositories.weights_repo import WeightRepository
from app.services.location_heatmap import LocationHeatmap
from app.services.preferences_bridge import PreferencesBridge
from app.database.session import get_session
from app.database.models.recommendation import UserInteraction
from app.database.models.property import SyncedProperty

router = APIRouter()

property_repo = PropertyRepository()
room_repo = RoomRepository()
user_repo = UserRepository()
questionnaire_repo = QuestionnaireRepository()
pref_repo = SearchPreferenceRepository()
rec_repo = RecommendationRepository()
interaction_repo = InteractionRepository()
match_repo = MatchingRepository()
questionnaire_service = QuestionnaireService()
property_recommender = PropertyRecommender()
room_recommender = RoomRecommender()
interaction_analyzer = InteractionAnalyzer()
user_classifier = UserClassifier()
matching_engine = CompatibilityEngine()
feedback_scorer = FeedbackScorer()
weight_repo = WeightRepository()
location_heatmap = LocationHeatmap()


def _build_context(prefs, answers=None):
    context = {"preferences": prefs}
    if answers:
        context["questionnaire_answers"] = [
            {"question_id": a.question_id, "answer_value": a.answer_value} for a in answers
        ]
    if prefs:
        context["max_budget"] = prefs.max_budget
        context["min_budget"] = prefs.min_budget
        context["preferred_city"] = prefs.preferred_city
        context["preferred_government"] = prefs.preferred_government
    return context


def _recompute(user_id, background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(_run_recommendations, user_id)


def _run_recommendations(user_id: str):
    properties = property_repo.get_all_approved()
    rooms = room_repo.get_available()
    user = user_repo.get_profile(user_id)
    prefs = pref_repo.get(user_id)
    answers = questionnaire_repo.get_answers(user_id)
    context = _build_context(prefs, answers)

    scored_props = property_recommender.recommend(user or prefs, properties, context)
    rec_repo.save_property_recommendations(user_id, scored_props)

    scored_rooms = room_recommender.recommend(user or prefs, rooms, context)
    rec_repo.save_room_recommendations(user_id, scored_rooms)


# --- SYNC ---

@router.post("/sync/refresh")
def trigger_sync():
    service = DataSyncService()
    results = service.sync_all()
    return {"status": "ok", "results": results}


@router.post("/sync/users")
def sync_users():
    service = DataSyncService()
    result = service.sync_users()
    pref_result = service.sync_user_preferences()
    return {"status": "ok", "users": result, "preferences": pref_result}


@router.get("/sync/status")
def sync_status():
    return {"status": "ok", "message": "Sync status endpoint"}


# --- RECOMMENDATIONS ---

def _apply_filters(scored, filters):
    city = filters.get("city")
    min_budget = filters.get("min_budget")
    max_budget = filters.get("max_budget")
    property_type = filters.get("property_type")
    limit = filters.get("limit")

    filtered = []
    for item in scored:
        prop = item[0]
        if city and getattr(prop, "city", "").lower() != city.lower():
            continue
        if min_budget is not None and (getattr(prop, "monthly_rent", 0) or 0) < min_budget:
            continue
        if max_budget is not None and (getattr(prop, "monthly_rent", 0) or 0) > max_budget:
            continue
        if property_type:
            type_map = {"full": 0, "shared": 1, "room": 1}
            mapped = type_map.get(property_type.lower())
            if mapped is not None and getattr(prop, "property_type", None) != mapped:
                continue
        filtered.append(item)

    if limit:
        filtered = filtered[:limit]

    return filtered


def _apply_room_filters(scored, filters):
    city = filters.get("city")
    limit = filters.get("limit")

    filtered = []
    for item in scored:
        room = item[0]
        prop = item[3]
        if city and prop is not None and getattr(prop, "city", "").lower() != city.lower():
            continue
        filtered.append(item)

    if limit:
        filtered = filtered[:limit]

    return filtered


@router.get("/recommend/properties/{user_id}")
def get_property_recommendations(
    user_id: str,
    city: str = Query(None),
    min_budget: float = Query(None),
    max_budget: float = Query(None),
    property_type: str = Query(None),
    limit: int = Query(None),
):
    user = user_repo.get_profile(user_id)
    prefs = pref_repo.get(user_id)

    if not user and not prefs:
        session = get_session()
        popular = (
            session.query(
                UserInteraction.target_id,
                func.count(UserInteraction.id).label("view_count")
            )
            .filter(
                UserInteraction.target_type == "property",
                UserInteraction.action.in_(["viewed", "liked", "saved", "contacted"])
            )
            .group_by(UserInteraction.target_id)
            .order_by(func.count(UserInteraction.id).desc())
            .limit(20)
            .all()
        )
        session.close()

        if popular:
            pop_ids = [p.target_id for p in popular]
            view_counts = {p.target_id: p.view_count for p in popular}
            all_props = property_repo.get_all_approved()
            prop_map = {p.id: p for p in all_props}
            max_count = max(view_counts.values()) if view_counts else 1
            recommendations = []
            for pid in pop_ids:
                prop = prop_map.get(pid)
                if prop:
                    popularity_score = view_counts.get(pid, 0) / max_count
                    recommendations.append({
                        "property_id": pid,
                        "score": popularity_score,
                        "score_breakdown": {"popularity": popularity_score},
                        "rank": len(recommendations),
                    })
            return {
                "user_id": user_id,
                "recommendations": recommendations,
            }

    properties = property_repo.get_all_approved()
    answers = questionnaire_repo.get_answers(user_id)
    context = _build_context(prefs, answers)

    filter_overrides = {}
    if city:
        filter_overrides["preferred_city"] = city
    if min_budget is not None:
        filter_overrides["min_budget"] = min_budget
    if max_budget is not None:
        filter_overrides["max_budget"] = max_budget
    if property_type:
        filter_overrides["preferred_property_type"] = property_type

    if filter_overrides:
        context.update(filter_overrides)

    scored = property_recommender.recommend(user or prefs, properties, context)
    scored = _apply_filters(scored, {
        "city": city,
        "min_budget": min_budget,
        "max_budget": max_budget,
        "property_type": property_type,
        "limit": limit,
    })
    rec_repo.save_property_recommendations(user_id, scored)

    return {
        "user_id": user_id,
        "recommendations": [
            {"property_id": p.id, "score": s, "score_breakdown": b, "rank": i}
            for i, (p, s, b) in enumerate(scored)
        ]
    }


@router.get("/recommend/rooms/{user_id}")
def get_room_recommendations(
    user_id: str,
    city: str = Query(None),
    limit: int = Query(None),
):
    rooms = room_repo.get_available()
    user = user_repo.get_profile(user_id)
    prefs = pref_repo.get(user_id)
    context = _build_context(prefs)

    if city:
        context["preferred_city"] = city

    scored = room_recommender.recommend(user or prefs, rooms, context)
    scored = _apply_room_filters(scored, {"city": city, "limit": limit})
    rec_repo.save_room_recommendations(user_id, scored)

    return {
        "user_id": user_id,
        "recommendations": [
            {"room_id": r.id, "property_id": getattr(p, "id", None), "score": s, "score_breakdown": b, "rank": i}
            for i, (r, s, b, p) in enumerate(scored)
        ]
    }


@router.post("/recommend/compute/{user_id}")
def compute_recommendations(user_id: str, background_tasks: BackgroundTasks):
    _recompute(user_id, background_tasks)
    return {"status": "ok", "message": f"Recomputing recommendations for {user_id}"}


# --- MATCHING ---

@router.post("/match/compute/{user_id}")
def compute_matches(user_id: str):
    result = matching_engine.compute_for_user(user_id)
    return result


@router.get("/match/results/{user_id}")
def get_match_results(user_id: str):
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
    user_repo.upsert_profile(data.user_id, data.model_dump(exclude={"user_id"}))
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
    pref_repo.upsert(data.user_id, data.model_dump(exclude={"user_id"}))
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
def submit_answers(user_id: str, data: QuestionnaireAnswersSubmit, background_tasks: BackgroundTasks):
    answers = [a.model_dump() for a in data.answers]
    questionnaire_repo.save_answers(user_id, answers)
    _recompute(user_id, background_tasks)
    return {"status": "ok", "user_id": user_id, "answers_count": len(answers), "recompute": "queued"}


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


# --- INTERACTION ANALYSIS & USER CLASSIFICATION ---

@router.post("/analyze/{user_id}")
def analyze_interactions(user_id: str):
    result = interaction_analyzer.analyze(user_id)
    return result


@router.get("/classify/{user_id}")
def classify_user(user_id: str):
    preferences = pref_repo.get(user_id)
    prefs_dict = {
        "preferred_city": preferences.preferred_city,
        "preferred_government": preferences.preferred_government,
        "preferred_property_type": preferences.preferred_property_type,
        "min_budget": preferences.min_budget,
        "max_budget": preferences.max_budget,
        "furnished": preferences.furnished,
    } if preferences else {}
    classification = user_classifier.classify(user_id, prefs_dict)
    return {"user_id": user_id, "classification": classification}


@router.post("/interactions/feedback/{user_id}")
def learn_from_interactions(user_id: str):
    feedback_scorer.learn_from_interaction(user_id, "", 0, "viewed")
    return {"status": "ok", "user_id": user_id}


@router.get("/heatmap/{user_id}")
def get_location_heatmap(user_id: str):
    result = location_heatmap.analyze(user_id)
    return result


@router.post("/admin/sync-preferences")
def sync_chatbot_preferences():
    bridge = PreferencesBridge()
    result = bridge.sync_all()
    return {"status": "ok", "synced": result}


# --- WEIGHTS (A/B Testing) ---

@router.get("/admin/weights")
def get_all_weights():
    weights = weight_repo.get_all_weights()
    return {
        "weights": [
            {
                "id": w.id,
                "key": w.weight_key,
                "value": w.weight_value,
                "group": w.weight_group,
                "description": w.description,
            }
            for w in weights
        ]
    }


@router.put("/admin/weights/{group}/{key}")
def update_weight(group: str, key: str, value: float = Query(...)):
    updated = weight_repo.update_weight(key, group, value)
    if not updated:
        raise HTTPException(status_code=404, detail="Weight not found")
    return {"status": "ok", "key": key, "group": group, "new_value": value}


@router.get("/admin/weights/{group}")
def get_group_weights(group: str):
    weights = weight_repo.get_weights(group)
    return {"group": group, "weights": weights}
