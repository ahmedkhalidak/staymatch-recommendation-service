"""
InteractionAnalyzer — learns user preferences from their behavior.
Uses dwell time, location patterns, and all lifetime interactions.
"""
from collections import Counter

from app.repositories.property_repo import InteractionRepository, SearchPreferenceRepository
from app.database.session import get_session
from app.database.models.recommendation import UserInteraction
from app.services.mssql_reader import get_properties_batch


INTERACTION_WEIGHTS = {
    "dwell_high": 3.0,
    "saved": 2.5,
    "liked": 2.0,
    "contacted": 2.0,
    "dwell_medium": 1.5,
    "viewed": 1.0,
    "skipped": 0.3,
}


def get_similar_properties(property_id: int, limit: int = 5) -> list[dict]:
    session = get_session()
    users_who_viewed = (
        session.query(UserInteraction.user_id)
        .filter(
            UserInteraction.target_type == "property",
            UserInteraction.target_id == property_id,
            UserInteraction.action.in_(["viewed", "liked", "saved", "contacted"]),
        )
        .distinct()
        .all()
    )
    user_ids = [u.user_id for u in users_who_viewed]
    if not user_ids:
        session.close()
        return []

    co_occurrence = (
        session.query(UserInteraction.target_id, UserInteraction.target_type)
        .filter(
            UserInteraction.user_id.in_(user_ids),
            UserInteraction.target_type == "property",
            UserInteraction.target_id != property_id,
            UserInteraction.action.in_(["viewed", "liked", "saved", "contacted"]),
        )
        .all()
    )
    session.close()

    counts = Counter()
    for target_id, _ in co_occurrence:
        counts[target_id] += 1

    top_ids = [pid for pid, _ in counts.most_common(limit)]
    properties = get_properties_batch(top_ids) if top_ids else []

    result = []
    for prop in properties:
        pid = prop.get("Id") or prop.get("id")
        result.append({
            "property_id": pid,
            "co_occurrence_count": counts.get(pid, 0),
            "details": prop,
        })
    return result


class InteractionAnalyzer:
    MIN_INTERACTIONS_FOR_ANALYSIS = 3

    def __init__(self):
        self.interaction_repo = InteractionRepository()
        self.pref_repo = SearchPreferenceRepository()

    def analyze(self, user_id: str):
        interactions = self.interaction_repo.get_by_user(user_id)
        if len(interactions) < self.MIN_INTERACTIONS_FOR_ANALYSIS:
            return {"status": "skipped", "reason": "not enough interactions", "count": len(interactions)}

        property_ids = []
        dwell_signals = {}
        for i in interactions:
            if i.target_type == "property":
                property_ids.append(i.target_id)
                if i.dwell_seconds and i.dwell_seconds >= 10:
                    dwell_signals[i.target_id] = i.dwell_seconds

        if not property_ids:
            return {"status": "skipped", "reason": "no property interactions", "count": len(interactions)}

        properties = get_properties_batch(list(set(property_ids)))
        if not properties:
            return {"status": "skipped", "reason": "no matching properties found in MSSQL", "count": len(property_ids)}

        weighted_prefs = self._extract_weighted_preferences(properties, interactions, dwell_signals)
        self.pref_repo.upsert(user_id, weighted_prefs)

        high_dwell_count = len([s for s in dwell_signals.values() if s >= 30])

        return {
            "status": "analyzed",
            "user_id": user_id,
            "interactions_analyzed": len(interactions),
            "properties_analyzed": len(properties),
            "high_dwell_properties": high_dwell_count,
            "inferred_preferences": weighted_prefs,
        }

    def _get_interaction_weight(self, action: str, dwell: int = 0) -> float:
        if dwell >= 30:
            return INTERACTION_WEIGHTS["dwell_high"]
        if dwell >= 10:
            return INTERACTION_WEIGHTS["dwell_medium"]
        return INTERACTION_WEIGHTS.get(action, 1.0)

    def _extract_weighted_preferences(self, properties: list[dict], interactions: list, dwell_signals: dict) -> dict:
        prefs = {}
        action_for_prop = {}
        dwell_props = set()

        for i in interactions:
            if i.target_type == "property":
                existing = action_for_prop.get(i.target_id)
                weight = self._get_interaction_weight(i.action, i.dwell_seconds or 0)
                if not existing or weight > existing[1]:
                    action_for_prop[i.target_id] = (i.action, weight, i.dwell_seconds or 0)
                if i.dwell_seconds and i.dwell_seconds >= 10:
                    dwell_props.add(i.target_id)
        for pid, secs in dwell_signals.items():
            if secs >= 10:
                dwell_props.add(pid)

        cities = Counter()
        governments = Counter()
        property_types = Counter()
        weighted_rents = []
        furnished_scores = []

        for prop in properties:
            pid = prop.get("Id") or prop.get("id")
            action_info = action_for_prop.get(pid)
            weight = action_info[1] if action_info else 1.0

            cities[prop.get("City") or "unknown"] += weight
            governments[prop.get("Government") or "unknown"] += weight
            ptype = prop.get("PropertyType")
            property_types["full" if ptype == 0 else "shared"] += weight

            rent = prop.get("MonthlyRent")
            if rent is not None:
                weighted_rents.append((float(rent), weight))

            if prop.get("Furnished"):
                furnished_scores.append(1.0 * weight)
            else:
                furnished_scores.append(0.0 * weight)

        if cities:
            top_city = cities.most_common(1)[0][0]
            if top_city != "unknown":
                prefs["preferred_city"] = top_city
        if governments:
            top_gov = governments.most_common(1)[0][0]
            if top_gov != "unknown":
                prefs["preferred_government"] = top_gov
        if property_types:
            prefs["preferred_property_type"] = property_types.most_common(1)[0][0]

        if weighted_rents:
            weighted_rents.sort(key=lambda x: x[0])
            total_w = sum(w for _, w in weighted_rents)
            if total_w > 0:
                avg_min = sum(r * w for r, w in weighted_rents[:max(1, len(weighted_rents)//3)]) / total_w
                avg_max = sum(r * w for r, w in weighted_rents[-max(1, len(weighted_rents)//3):]) / total_w
                prefs["min_budget"] = int(avg_min * 0.9)
                prefs["max_budget"] = int(avg_max * 1.1)

        if furnished_scores and len(properties) > 0:
            avg_furnished = sum(furnished_scores) / sum(self._get_interaction_weight("viewed") for _ in properties)
            prefs["furnished"] = avg_furnished >= 0.4

        self._extract_amenities(properties, interactions, prefs)

        prefs["_dwell_high_count"] = len(dwell_props)

        return prefs

    def _extract_amenities(self, properties: list[dict], interactions: list, prefs: dict):
        amenities = {"wifi": 0, "air_conditioning": 0, "balcony": 0, "washer": 0, "refrigerator": 0}
        total = len(properties)
        for prop in properties:
            am = prop.get("amenities", {})
            for key in amenities:
                if am.get(key) or am.get(key.title()):
                    amenities[key] += 1
        for key, count in amenities.items():
            if total > 0 and count / total >= 0.5:
                prefs[key] = True


class UserClassifier:
    def __init__(self):
        self.session = get_session()
        self.interaction_repo = InteractionRepository()

    def classify(self, user_id: str, preferences: dict = None) -> dict:
        classification = {"segments": [], "traits": {}}

        interactions = self.interaction_repo.get_by_user(user_id)
        total = len(interactions)

        if total == 0:
            return classification

        actions = Counter(i.action for i in interactions)
        save_ratio = actions.get("saved", 0) / total if total > 0 else 0
        view_ratio = actions.get("viewed", 0) / total if total > 0 else 0

        dwell_sessions = [i for i in interactions if i.dwell_seconds and i.dwell_seconds >= 10]
        dwell_30 = len([i for i in dwell_sessions if i.dwell_seconds >= 30])
        high_dwell_ratio = dwell_30 / total if total > 0 else 0

        if high_dwell_ratio > 0.2:
            classification["segments"].append("careful_evaluator")
        elif save_ratio > 0.25:
            classification["segments"].append("decisive_buyer")
        elif view_ratio > 0.7:
            classification["segments"].append("explorer_browser")
        else:
            classification["segments"].append("balanced_browser")

        if dwell_30 >= 5:
            classification["segments"].append("high_interest_user")

        if preferences:
            ptype = preferences.get("preferred_property_type", "")
            if ptype == "shared":
                classification["segments"].append("budget_conscious")
            elif ptype == "full":
                classification["segments"].append("privacy_seeker")

            if preferences.get("max_budget", 0) > 0:
                if preferences["max_budget"] > 10000:
                    classification["segments"].append("premium_segment")
                elif preferences["max_budget"] < 3000:
                    classification["segments"].append("budget_conscious")

        classification["traits"] = {
            "lifetime_interactions": total,
            "high_dwell_count": dwell_30,
            "view_ratio": round(view_ratio, 2),
            "save_ratio": round(save_ratio, 2),
        }

        return classification
