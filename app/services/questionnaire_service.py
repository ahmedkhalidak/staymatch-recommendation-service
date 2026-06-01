from app.database.session import get_session
from app.database.models.user import QuestionnaireCategory, QuestionnaireQuestion


class QuestionnaireService:
    def __init__(self):
        self.session = get_session()

    def get_all_questions(self):
        categories = self.session.query(QuestionnaireCategory).order_by(QuestionnaireCategory.sort_order).all()
        result = []
        for cat in categories:
            questions = self.session.query(QuestionnaireQuestion).filter(
                QuestionnaireQuestion.category_id == cat.id,
                QuestionnaireQuestion.is_active == True
            ).order_by(QuestionnaireQuestion.sort_order).all()
            result.append({
                "category": {
                    "id": cat.id,
                    "name_ar": cat.name_ar,
                    "name_en": cat.name_en,
                },
                "questions": [
                    {
                        "id": q.id,
                        "question_ar": q.question_ar,
                        "question_en": q.question_en,
                        "question_type": q.question_type,
                        "options_ar": q.options_ar,
                        "options_en": q.options_en,
                        "weight": q.weight,
                    }
                    for q in questions
                ]
            })
        return result