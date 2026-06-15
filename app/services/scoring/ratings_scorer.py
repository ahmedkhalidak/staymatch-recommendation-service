from app.services.scoring.base_scorer import BaseScorer


class RatingsScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        avg = getattr(candidate, "average_rating", None)
        count = getattr(candidate, "review_count", 0)
        if avg is None or count == 0:
            return 0.5
        bayesian = (avg * count + 3.5 * 5) / (count + 5)
        return (bayesian - 1.0) / 4.0