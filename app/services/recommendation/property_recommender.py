from datetime import datetime, timedelta

from app.utils.weights import PROPERTY_WEIGHTS, ROOM_WEIGHTS
from app.services.ranking.ranker import Ranker
from app.services.scoring.budget_scorer import BudgetScorer
from app.services.scoring.location_scorer import LocationScorer
from app.services.scoring.amenity_scorer import AmenityScorer
from app.services.scoring.tenant_scorer import TenantScorer
from app.services.scoring.questionnaire_scorer import QuestionnaireScorer


class PropertyRecommender:
    def __init__(self):
        self.ranker = Ranker(PROPERTY_WEIGHTS)
        self.budget_scorer = BudgetScorer()
        self.location_scorer = LocationScorer()
        self.amenity_scorer = AmenityScorer()
        self.tenant_scorer = TenantScorer()
        self.questionnaire_scorer = QuestionnaireScorer()

    def recommend(self, user, properties, context=None):
        scored = []
        for prop in properties:
            score_context = context or {}
            score_context["amenities"] = getattr(prop, "amenities", None)
            score_context["allowed_tenants"] = getattr(prop, "allowed_tenants", None)

            breakdown = {
                "budget": self.budget_scorer.score(user, prop, score_context),
                "location": self.location_scorer.score(user, prop, score_context),
                "amenities": self.amenity_scorer.score(user, prop, score_context),
                "tenant": self.tenant_scorer.score(user, prop, score_context),
                "furnished": 1.0 if getattr(prop, "furnished", False) else 0.5,
                "property_type": self._type_score(user, prop),
                "recency": self._recency_score(prop),
            }

            total = self.ranker.weighted_sum(breakdown)
            scored.append((prop, total, breakdown))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

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
        self.ranker = Ranker(ROOM_WEIGHTS)
        self.budget_scorer = BudgetScorer()
        self.location_scorer = LocationScorer()
        self.amenity_scorer = AmenityScorer()
        self.tenant_scorer = TenantScorer()

    def recommend(self, user, rooms, context=None):
        scored = []
        for room in rooms:
            property_obj = getattr(room, "property", None)
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

            total = self.ranker.weighted_sum(breakdown)
            scored.append((room, total, breakdown, property_obj))

        scored.sort(key=lambda x: x[1], reverse=True)
        return self._apply_diversity(scored)

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