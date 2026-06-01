from app.repositories.weights_repo import WeightRepository


class Ranker:
    def __init__(self, weights: dict[str, float] = None, group: str = None):
        self.weights = weights or {}
        self.group = group
        self._weight_repo = WeightRepository() if group else None

    def _load_weights(self):
        if self._weight_repo and self.group:
            db_weights = self._weight_repo.get_weights(self.group)
            if db_weights:
                self.weights = db_weights

    def weighted_sum(self, score_breakdown: dict[str, float]) -> float:
        if self._weight_repo:
            self._load_weights()
        total = 0.0
        weight_sum = 0.0
        for key, score in score_breakdown.items():
            w = self.weights.get(key, 0.0)
            total += w * score
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0