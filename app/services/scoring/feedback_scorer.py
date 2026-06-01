"""
FeedbackScorer — reads user interaction history and applies boost/penalty.
When a user saves/likes a property, similar properties get a boost.
When a user skips a property, similar properties get a penalty.
Stores learned preferences in user_feedback_weights for the ranker.
"""
from collections import Counter
from datetime import datetime, timedelta

from app.database.session import get_session
from app.database.models.recommendation import UserInteraction
from app.repositories.weights_repo import FeedbackRepository
from app.services.mssql_reader import get_properties_batch


class FeedbackScorer:
    BOOST_SAVE = 1.3
    BOOST_LIKE = 1.2
    BOOST_VIEW = 1.05
    PENALTY_SKIP = 0.7

    def __init__(self):
        self.session = get_session()
        self.feedback_repo = FeedbackRepository()

    def compute_boost(self, user_id: str, property_id: int) -> float:
        feedback = self.feedback_repo.get_user_feedback(user_id)
        if feedback and feedback.boost_factor and feedback.boost_factor != 1.0:
            return feedback.boost_factor
        return 1.0

    def learn_from_interaction(self, user_id: str, target_type: str, target_id: int, action: str, context: dict = None):
        if action not in ("viewed", "saved", "liked", "skipped"):
            return

        recent = self.session.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()

        if recent < 3:
            return

        property_ids = []
        interactions = self.session.query(UserInteraction).filter(
            UserInteraction.user_id == user_id,
            UserInteraction.target_type == "property",
            UserInteraction.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).all()

        if not interactions:
            return

        save_count = sum(1 for i in interactions if i.action == "saved")
        like_count = sum(1 for i in interactions if i.action == "liked")
        skip_count = sum(1 for i in interactions if i.action == "skipped")

        if save_count + like_count < 2:
            return

        properties = get_properties_batch([i.target_id for i in interactions if i.target_type == "property"])
        if not properties:
            return

        cities = Counter()
        governments = Counter()
        ptypes = Counter()
        rents = []
        for p in properties:
            cities[p.get("City") or "unknown"] += 1
            governments[p.get("Government") or "unknown"] += 1
            ptypes[p.get("PropertyType")] += 1
            if p.get("MonthlyRent"):
                rents.append(float(p["MonthlyRent"]))

        data = {}
        if cities:
            top_city = cities.most_common(1)[0][0]
            if top_city != "unknown":
                data["city"] = top_city
        if governments:
            top_gov = governments.most_common(1)[0][0]
            if top_gov != "unknown":
                data["government"] = top_gov
        if ptypes:
            data["property_type"] = ptypes.most_common(1)[0][0]
        if rents:
            rents.sort()
            data["min_budget"] = int(rents[0] * 0.85)
            data["max_budget"] = int(rents[-1] * 1.15)

        positive = save_count + like_count
        negative = skip_count
        total = positive + negative
        if total > 0:
            ratio = positive / total
            if ratio > 0.7:
                data["boost_factor"] = self.BOOST_SAVE
            elif ratio > 0.5:
                data["boost_factor"] = self.BOOST_LIKE
            elif ratio < 0.3:
                data["boost_factor"] = self.PENALTY_SKIP

        if len(data) > 1:
            self.feedback_repo.upsert_feedback(user_id, data)