from app.services.scoring.base_scorer import BaseScorer


class CompatibilityEngine:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def compute_pairwise(self, seeker_answers: dict, roommate_answers: dict) -> float:
        return self._questionnaire_similarity(seeker_answers, roommate_answers)

    def _questionnaire_similarity(self, answers_a: dict, answers_b: dict) -> float:
        shared_questions = set(answers_a.keys()) & set(answers_b.keys())
        if not shared_questions:
            return 0.5

        total_score = 0.0
        for qid in shared_questions:
            a_val = answers_a[qid]
            b_val = answers_b[qid]
            if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                if a_val <= 5 and b_val <= 5:
                    similarity = 1.0 - abs(a_val - b_val) / 4.0
                else:
                    similarity = 1.0 if a_val == b_val else 0.0
            else:
                similarity = 1.0 if str(a_val).lower() == str(b_val).lower() else 0.0
            total_score += similarity

        return total_score / len(shared_questions)


class RoomScoreAggregator:
    def aggregate(self, pairwise_scores: list[float], capacity_available: int) -> float:
        if not pairwise_scores:
            return 0.5
        avg = sum(pairwise_scores) / len(pairwise_scores)
        capacity_factor = min(1.0, capacity_available / 3.0)
        return avg * (0.7 + 0.3 * capacity_factor)