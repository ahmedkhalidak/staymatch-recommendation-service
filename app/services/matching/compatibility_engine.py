from datetime import datetime, timedelta
import math

from app.database.session import get_session
from app.database.models.user import UserProfile, UserQuestionnaireAnswer, UserSearchPreference
from app.database.models.recommendation import RoommateMatch
from app.repositories.property_repo import MatchingRepository, QuestionnaireRepository
from app.database.models.property import SyncedRoom

MATCHING_WEIGHTS = {
    "questionnaire": 0.50,
    "gender": 0.15,
    "occupation": 0.10,
    "age_group": 0.10,
    "lifestyle": 0.15,
}

LIFESTYLE_QUESTION_IDS = {4, 5, 6, 7, 8}


class CompatibilityEngine:
    def __init__(self):
        self.session = get_session()
        self.match_repo = MatchingRepository()
        self.questionnaire_repo = QuestionnaireRepository()
        self.weights = MATCHING_WEIGHTS

    def compute_for_user(self, seeker_id: str) -> dict:
        seeker_answers = self._get_answers_as_dict(seeker_id)
        seeker_profile = self.session.query(UserProfile).filter(
            UserProfile.external_user_id == seeker_id
        ).first()

        if not seeker_answers:
            return {"status": "skipped", "reason": "no questionnaire answers", "matches": []}

        rooms = self.session.query(SyncedRoom).filter(
            SyncedRoom.is_deleted == False,
            SyncedRoom.capacity_available > 0
        ).all()

        matches = []
        for room in rooms:
            all_users = self.session.query(UserProfile).filter(
                UserProfile.external_user_id != seeker_id
            ).all()

            pairwise_scores = []
            roommate_details = []

            for other in all_users:
                other_answers = self._get_answers_as_dict(other.external_user_id)
                if not other_answers:
                    continue

                score = self._compute_pairwise(
                    seeker_answers, other_answers,
                    seeker_profile, other
                )

                if score >= 0.3:
                    pairwise_scores.append(score)
                    roommate_details.append({
                        "user_id": other.external_user_id,
                        "score": round(score, 4)
                    })

            if pairwise_scores:
                room_score = self._aggregate_room_score(pairwise_scores, room.capacity_available)
                match_data = {
                    "seeker_user_id": seeker_id,
                    "room_id": room.id,
                    "property_id": room.property_id,
                    "room_compatibility_score": round(room_score, 4),
                    "match_breakdown": {
                        "pairwise_scores": [round(s, 4) for s in pairwise_scores],
                        "average_pairwise": round(sum(pairwise_scores) / len(pairwise_scores), 4),
                        "num_roommates": len(pairwise_scores),
                    },
                    "current_roommates": roommate_details,
                    "seeker_questionnaire_match": round(sum(pairwise_scores) / len(pairwise_scores), 4),
                }
                self.match_repo.save_match(match_data)
                matches.append({
                    "room_id": room.id,
                    "property_id": room.property_id,
                    "room_compatibility_score": round(room_score, 4),
                    "roommate_count": len(pairwise_scores),
                })

        matches.sort(key=lambda m: m["room_compatibility_score"], reverse=True)
        return {"status": "completed", "seeker_user_id": seeker_id, "matches_count": len(matches), "matches": matches}

    def _compute_pairwise(self, answers_a: dict, answers_b: dict, profile_a=None, profile_b=None) -> float:
        questionnaire_sim = self._questionnaire_similarity(answers_a, answers_b)
        lifestyle_sim = self._lifestyle_similarity(answers_a, answers_b)

        gender_sim = 1.0
        if profile_a and profile_b and profile_a.gender and profile_b.gender:
            gender_sim = 1.0 if profile_a.gender.lower() == profile_b.gender.lower() else 0.3

        occupation_sim = 1.0
        if profile_a and profile_b and profile_a.occupation and profile_b.occupation:
            occupation_sim = 1.0 if profile_a.occupation.lower() == profile_b.occupation.lower() else 0.4

        age_sim = 1.0
        if profile_a and profile_b and profile_a.birth_year and profile_b.birth_year:
            age_diff = abs(profile_a.birth_year - profile_b.birth_year)
            age_sim = max(0.0, 1.0 - age_diff / 20.0)

        total = (
            self.weights["questionnaire"] * questionnaire_sim +
            self.weights["gender"] * gender_sim +
            self.weights["occupation"] * occupation_sim +
            self.weights["age_group"] * age_sim +
            self.weights["lifestyle"] * lifestyle_sim
        )
        weight_sum = (self.weights["questionnaire"] + self.weights["gender"] +
                      self.weights["occupation"] + self.weights["age_group"] +
                      self.weights["lifestyle"])
        return total / weight_sum if weight_sum > 0 else 0.5

    def _lifestyle_similarity(self, answers_a: dict, answers_b: dict) -> float:
        lifestyle_keys_a = {k: v for k, v in answers_a.items() if int(k) in LIFESTYLE_QUESTION_IDS}
        lifestyle_keys_b = {k: v for k, v in answers_b.items() if int(k) in LIFESTYLE_QUESTION_IDS}
        shared = set(lifestyle_keys_a.keys()) & set(lifestyle_keys_b.keys())
        if not shared:
            return 0.5
        total = 0.0
        for qid in shared:
            a_val = lifestyle_keys_a[qid]
            b_val = lifestyle_keys_b[qid]
            if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                if 1 <= a_val <= 5 and 1 <= b_val <= 5:
                    sim = 1.0 - abs(a_val - b_val) / 4.0
                else:
                    sim = 1.0 if a_val == b_val else 0.0
            else:
                sim = 1.0 if str(a_val).strip().lower() == str(b_val).strip().lower() else 0.0
            total += sim
        return total / len(shared)

    def _questionnaire_similarity(self, answers_a: dict, answers_b: dict) -> float:
        shared = set(answers_a.keys()) & set(answers_b.keys())
        if not shared:
            return 0.5

        total = 0.0
        for qid in shared:
            a_val = answers_a[qid]
            b_val = answers_b[qid]
            if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                if 1 <= a_val <= 5 and 1 <= b_val <= 5:
                    sim = 1.0 - abs(a_val - b_val) / 4.0
                else:
                    sim = 1.0 if a_val == b_val else 0.0
            else:
                sim = 1.0 if str(a_val).strip().lower() == str(b_val).strip().lower() else 0.0
            total += sim
        return total / len(shared)

    def _aggregate_room_score(self, pairwise_scores: list[float], capacity_available: int) -> float:
        if not pairwise_scores:
            return 0.5
        avg = sum(pairwise_scores) / len(pairwise_scores)
        capacity_factor = min(1.0, capacity_available / 3.0)
        return avg * (0.7 + 0.3 * capacity_factor)

    def _get_answers_as_dict(self, user_id: str) -> dict:
        answers = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).all()
        result = {}
        for a in answers:
            val = a.answer_scale if a.answer_scale is not None else a.answer_value
            result[str(a.question_id)] = val
        return result
