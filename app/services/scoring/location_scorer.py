from app.services.scoring.base_scorer import BaseScorer
from app.utils.location import geo_distance, governorate_center


class LocationScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        user_city = None
        user_gov = None

        if hasattr(user, "preferred_city") and user.preferred_city:
            user_city = user.preferred_city
            user_gov = getattr(user, "preferred_government", None) or user_city
        elif hasattr(user, "preferred_government") and user.preferred_government:
            user_gov = user.preferred_government
        elif context and isinstance(context, dict):
            user_city = context.get("preferred_city")
            user_gov = context.get("preferred_government")

        if not user_city and not user_gov:
            return 0.5

        prop_city = getattr(candidate, "city", None) or ""
        prop_gov = getattr(candidate, "government", None) or ""

        city_match = user_city and prop_city and user_city.lower() == prop_city.lower()
        gov_match = user_gov and prop_gov and user_gov.lower() == prop_gov.lower()

        if city_match or gov_match:
            return 1.0

        if user_gov and prop_gov:
            user_center = governorate_center(user_gov)
            prop_center = governorate_center(prop_gov)
            if user_center and prop_center:
                distance = geo_distance(user_center[0], user_center[1], prop_center[0], prop_center[1])
                return max(0.0, 1.0 - distance / 200.0)

        return 0.0
