from app.repositories.property_repo import QuestionnaireRepository


class QuestionnaireService:
    def __init__(self):
        self.repo = QuestionnaireRepository()

    def get_all_questions(self):
        categories = self.repo.get_categories()
        result = []
        for cat in categories:
            questions = cat.questions if hasattr(cat, "questions") and cat.questions else []
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