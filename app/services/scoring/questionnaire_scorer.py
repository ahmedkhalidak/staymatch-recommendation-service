from app.services.scoring.base_scorer import BaseScorer


class QuestionnaireScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        answers = context.get("questionnaire_answers") if context else None
        if answers and len(answers) >= 5:
            return 0.6
        return 0.5