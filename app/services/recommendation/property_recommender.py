from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload

from app.utils.weights import PROPERTY_WEIGHTS, ROOM_WEIGHTS
from app.services.ranking.ranker import Ranker
from app.services.scoring.budget_scorer import BudgetScorer
from app.services.scoring.location_scorer import LocationScorer
from app.services.scoring.amenity_scorer import AmenityScorer
from app.services.scoring.tenant_scorer import TenantScorer
from app.services.scoring.questionnaire_scorer import QuestionnaireScorer
from app.database.session import get_session
from app.database.models.recommendation import PropertyRecommendation, RoomRecommendation


class PropertyRecommender:
    def __init__(self):
        self.ranker = Ranker(PROPERTY_WEIGHTS, group="property")
        self.budget_scorer = BudgetScorer()
        self.location_scorer = LocationScorer()
        self.amenity_scorer = AmenityScorer()
        self.tenant_scorer = TenantScorer()
        self.questionnaire_scorer = QuestionnaireScorer()

    def _get_user_id(self, user, context):
        if user is not None:
            uid = getattr(user, "external_user_id", None) or getattr(user, "user_id", None)
            if uid:
                return uid
        if context:
            return context.get("user_id")
        return None

    def _check_cache(self, user_id):
        if not user_id:
            return None
        session = get_session()
        cached = session.query(PropertyRecommendation).filter(
            PropertyRecommendation.user_id == user_id
        ).order_by(PropertyRecommendation.rank).all()
        session.close()
        if not cached:
            return None
        age = datetime.utcnow() - cached[0].created_at
        if age.total_seconds() >= 3600:
            return None
        return cached

    def _prefilter(self, user, properties):
        filtered = list(properties)
        preferred_city = None
        max_budget = None
        if user is not None:
            preferred_city = getattr(user, "preferred_city", None)
            max_budget = getattr(user, "max_budget", None)
        if preferred_city:
            filtered = [p for p in filtered if getattr(p, "city", "").lower() == preferred_city.lower()]
        if max_budget:
            filtered = [p for p in filtered if (getattr(p, "monthly_rent", 0) or 0) <= max_budget * 1.5]
        return filtered

    def recommend(self, user, properties, context=None):
        cached = self._check_cache(self._get_user_id(user, context))
        if cached:
            prop_map = {p.id: p for p in properties}
            result = []
            for c in cached:
                p = prop_map.get(c.property_id)
                if p:
                    result.append((p, c.score, c.score_breakdown))
            if result:
                return result

        prefiltered = self._prefilter(user, properties)
        candidates = prefiltered if prefiltered else properties

        scored = []
        for prop in candidates:
            score_context = context or {}
            score_context["amenities"] = prop.amenities if hasattr(prop, "amenities") else None
            score_context["allowed_tenants"] = prop.allowed_tenants if hasattr(prop, "allowed_tenants") else None

            breakdown = {
                "budget": self.budget_scorer.score(user, prop, score_context),
                "location": self.location_scorer.score(user, prop, score_context),
                "amenities": self.amenity_scorer.score(user, prop, score_context),
                "tenant": self.tenant_scorer.score(user, prop, score_context),
                "furnished": 1.0 if getattr(prop, "furnished", False) else 0.5,
                "property_type": self._type_score(user, prop),
                "recency": self._recency_score(prop),
            }

            if context and context.get("questionnaire_answers"):
                breakdown["questionnaire"] = self.questionnaire_scorer.score(user, prop, score_context)

            total = self.ranker.weighted_sum(breakdown)
            scored.append((prop, total, breakdown))

        scored = self._session_boost(scored, context)
        scored = self._apply_diversity(scored)
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _apply_diversity(self, scored, max_per_city=3):
        city_count = {}
        result = []
        for item in scored:
            prop = item[0]
            city = getattr(prop, "city", None) or "unknown"
            current = city_count.get(city, 0)
            if current < max_per_city:
                city_count[city] = current + 1
                result.append(item)
        return result

    def _session_boost(self, scored, context):
        if not context:
            return scored
        recent_searches = context.get("recent_searches")
        if not recent_searches:
            return scored
        boosted = []
        for prop, total, breakdown in scored:
            boost = 0.0
            for search in recent_searches:
                city = search.get("city", "").lower()
                government = search.get("government", "").lower()
                prop_city = (getattr(prop, "city", "") or "").lower()
                prop_gov = (getattr(prop, "government", "") or "").lower()
                if (city and city == prop_city) or (government and government == prop_gov):
                    boost = max(boost, 0.1)
            adjusted = total + boost
            boosted.append((prop, adjusted, breakdown))
        return boosted

    def _type_score(self, user, prop):
        pref = getattr(user, "preferred_property_type", None)
        if not pref:
            return 0.5
        type_map = {"full": 0, "shared": 1, "room": 1}
        mapped = type_map.get(pref.lower())
        if mapped is not None and mapped == prop.property_type:
            return 1.0
        return 0.0

    def _recency_score(self, prop):
        created = getattr(prop, "created_at", None)
        if created is None:
            return 0.5
        days_old = (datetime.utcnow() - created).days
        if days_old <= 7:
            return 1.0
        if days_old <= 30:
            return 0.8
        if days_old <= 90:
            return 0.5
        return 0.2


class RoomRecommender:
    def __init__(self):
        self.ranker = Ranker(ROOM_WEIGHTS, group="room")
        self.budget_scorer = BudgetScorer()
        self.location_scorer = LocationScorer()
        self.amenity_scorer = AmenityScorer()
        self.tenant_scorer = TenantScorer()
        self.questionnaire_scorer = QuestionnaireScorer()

    def _get_user_id(self, user, context):
        if user is not None:
            uid = getattr(user, "external_user_id", None) or getattr(user, "user_id", None)
            if uid:
                return uid
        if context:
            return context.get("user_id")
        return None

    def _check_cache(self, user_id):
        if not user_id:
            return None
        session = get_session()
        cached = session.query(RoomRecommendation).filter(
            RoomRecommendation.user_id == user_id
        ).order_by(RoomRecommendation.rank).all()
        session.close()
        if not cached:
            return None
        age = datetime.utcnow() - cached[0].created_at
        if age.total_seconds() >= 3600:
            return None
        return cached

    def recommend(self, user, rooms, context=None):
        cached = self._check_cache(self._get_user_id(user, context))
        if cached:
            room_map = {r.id: r for r in rooms}
            result = []
            for c in cached:
                r = room_map.get(c.room_id)
                if r:
                    prop = getattr(r, "property", None)
                    result.append((r, c.score, c.score_breakdown, prop))
            if result:
                return result

        scored = []
        for room in rooms:
            property_obj = room.property if hasattr(room, "property") else None
            score_context = context or {}
            score_context["allowed_tenants"] = self._get_room_tenants(room)

            breakdown = {
                "budget": self.budget_scorer.score(user, room, score_context),
                "location": self.location_scorer.score(user, property_obj, score_context) if property_obj else 0.5,
                "capacity": self._capacity_score(room),
                "amenities": self.amenity_scorer.score(user, property_obj, score_context) if property_obj else 0.5,
                "tenant": self.tenant_scorer.score(user, room, score_context),
                "furnished": 1.0 if getattr(room, "furnished", False) else 0.5,
                "room_type": self._room_type_score(room),
                "recency": self._recency_score(room),
            }

            if context and context.get("questionnaire_answers"):
                breakdown["questionnaire"] = self.questionnaire_scorer.score(user, room, score_context)

            total = self.ranker.weighted_sum(breakdown)
            scored.append((room, total, breakdown, property_obj))

        scored = self._session_boost(scored, context)
        scored.sort(key=lambda x: x[1], reverse=True)
        return self._apply_diversity(scored)

    def _session_boost(self, scored, context):
        if not context:
            return scored
        recent_searches = context.get("recent_searches")
        if not recent_searches:
            return scored
        boosted = []
        for room, total, breakdown, prop in scored:
            boost = 0.0
            for search in recent_searches:
                city = search.get("city", "").lower()
                government = search.get("government", "").lower()
                prop_city = (getattr(prop, "city", "") or "").lower() if prop else ""
                prop_gov = (getattr(prop, "government", "") or "").lower() if prop else ""
                if (city and city == prop_city) or (government and government == prop_gov):
                    boost = max(boost, 0.1)
            adjusted = total + boost
            boosted.append((room, adjusted, breakdown, prop))
        return boosted

    def _capacity_score(self, room):
        available = getattr(room, "capacity_available", 0)
        if available is None:
            return 0.5
        if available > 2:
            return 1.0
        if available > 0:
            return 0.8
        return 0.0

    def _room_type_score(self, room):
        if getattr(room, "ensuite_bathroom", False):
            return 1.0
        if getattr(room, "shared_bathroom", False):
            return 0.7
        return 0.5

    def _recency_score(self, room):
        created = getattr(room, "created_at", None)
        if created is None:
            return 0.5
        days_old = (datetime.utcnow() - created).days
        if days_old <= 7:
            return 1.0
        if days_old <= 30:
            return 0.8
        return 0.5

    def _get_room_tenants(self, room):
        tenants = getattr(room, "allowed_tenants", None)
        if tenants and len(tenants) > 0:
            return tenants[0]
        return None

    def _apply_diversity(self, scored, max_per_property=2):
        property_count = {}
        result = []
        for item in scored:
            room = item[0]
            prop = item[3]
            prop_id = getattr(prop, "id", None) if prop else None
            if prop_id is None:
                result.append(item)
                continue
            current = property_count.get(prop_id, 0)
            if current < max_per_property:
                property_count[prop_id] = current + 1
                result.append(item)
        return result
