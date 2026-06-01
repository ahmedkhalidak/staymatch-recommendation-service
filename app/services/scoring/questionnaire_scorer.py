from app.services.scoring.base_scorer import BaseScorer


class QuestionnaireScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        answers = context.get("questionnaire_answers") if context else None
        if not answers:
            return 0.5

        preferred_type = None
        for answer in answers:
            if answer.get("question_id") in (1, 2):
                preferred_type = answer.get("answer_value", "").lower()
                break

        property_type = getattr(candidate, "property_type", None)
        if property_type is not None and preferred_type:
            type_map = {"full_apartment": 0, "shared_housing": 1, "full": 0, "shared": 1, "room": 1}
            mapped = type_map.get(preferred_type)
            if mapped is not None and mapped == property_type:
                return 1.0
            if mapped is not None:
                return 0.3

        return 0.5