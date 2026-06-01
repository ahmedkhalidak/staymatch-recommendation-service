class Ranker:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def weighted_sum(self, score_breakdown: dict[str, float]) -> float:
        total = 0.0
        weight_sum = 0.0
        for key, score in score_breakdown.items():
            w = self.weights.get(key, 0.0)
            total += w * score
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0