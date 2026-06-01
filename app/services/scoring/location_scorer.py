from app.services.scoring.base_scorer import BaseScorer
from app.utils.location import geo_distance, governorate_center


class LocationScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        user_city = getattr(user, "preferred_city", None) or getattr(context, "preferred_city", None)
        user_gov = getattr(user, "preferred_government", None) or getattr(context, "preferred_government", None)

        if user_city is None and user_gov is None:
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