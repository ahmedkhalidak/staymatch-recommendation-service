from app.services.scoring.base_scorer import BaseScorer


class AmenityScorer(BaseScorer):
    AMENITY_FIELDS = ["wifi", "air_conditioning", "balcony", "private_bathroom"]

    def score(self, user, candidate, context=None):
        user_amenities = self._get_user_amenities(user, context)
        if not user_amenities:
            return 0.5

        property_amenities = context.get("amenities") if context else None
        if property_amenities is None:
            return 0.5

        matched = 0
        total = len(user_amenities)

        for amenity in user_amenities:
            attr = amenity.replace(" ", "_")
            am_value = getattr(property_amenities, attr, None)
            if am_value is None and candidate is not None:
                am_value = getattr(candidate, attr, None)
            if am_value:
                matched += 1

        return matched / total if total > 0 else 0.5

    def _get_user_amenities(self, user, context):
        amenities = []
        pref = context.get("preferences") if context else None
        source = pref or user
        for field in self.AMENITY_FIELDS:
            if hasattr(source, field) and getattr(source, field):
                amenities.append(field)
        if hasattr(source, "furnished") and getattr(source, "furnished"):
            amenities.append("furnished")
        return amenities
