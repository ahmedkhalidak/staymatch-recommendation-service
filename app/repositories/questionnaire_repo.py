"""Questionnaire repository for managing questionnaire data."""
from sqlalchemy.orm import joinedload

from app.database.session import get_session
from app.database.models.user import (
    QuestionnaireCategory,
    QuestionnaireQuestion,
    UserQuestionnaireAnswer,
)


class QuestionnaireRepository:
    """Repository for questionnaire-related operations."""

    def __init__(self):
        self.session = get_session()

    def get_categories(self):
        """Get all questionnaire categories with their questions."""
        return self.session.query(QuestionnaireCategory)\
            .options(joinedload(QuestionnaireCategory.questions))\
            .order_by(QuestionnaireCategory.sort_order).all()

    def get_questions(self, category_id: int = None):
        """Get active questions, optionally filtered by category."""
        query = self.session.query(QuestionnaireQuestion).filter(QuestionnaireQuestion.is_active == True)
        if category_id:
            query = query.filter(QuestionnaireQuestion.category_id == category_id)
        return query.order_by(QuestionnaireQuestion.sort_order).all()

    def save_answers(self, user_id: str, answers: list[dict]):
        """Save or update questionnaire answers for a user."""
        question_ids = [a["question_id"] for a in answers]
        existing_answers = {
            a.question_id: a
            for a in self.session.query(UserQuestionnaireAnswer).filter(
                UserQuestionnaireAnswer.user_id == user_id,
                UserQuestionnaireAnswer.question_id.in_(question_ids)
            ).all()
        }
        for answer in answers:
            existing = existing_answers.get(answer["question_id"])
            if existing:
                existing.answer_value = answer["answer_value"]
                existing.answer_scale = answer.get("answer_scale")
            else:
                self.session.add(UserQuestionnaireAnswer(
                    user_id=user_id,
                    question_id=answer["question_id"],
                    answer_value=answer["answer_value"],
                    answer_scale=answer.get("answer_scale")
                ))
        self.session.commit()

    def get_answers(self, user_id: str):
        """Get all questionnaire answers for a user."""
        return self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).all()

    def get_active_question_weights(self) -> dict[int, float]:
        """Load weights for all active questions from database."""
        questions = self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.is_active == True
        ).all()
        return {q.id: q.weight for q in questions}

    def get_active_question_metadata(self) -> dict:
        """Load metadata for all active questions including type, options, and text."""
        questions = self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.is_active == True
        ).all()
        return {
            q.id: {
                "question_type": q.question_type,
                "options_ar": q.options_ar,
                "options_en": q.options_en,
                "weight": q.weight,
                "question_en": q.question_en,
                "question_ar": q.question_ar,
                "matching_key": getattr(q, "matching_key", None),
            }
            for q in questions
        }

    def get_question_by_matching_key(self, matching_key: str):
        """Get a question by its matching_key."""
        return self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.matching_key == matching_key,
            QuestionnaireQuestion.is_active == True
        ).first()

    def get_questionnaire_status(self, user_id: str) -> dict:
        """Get questionnaire completion status for a user by counting answers."""
        total_questions = self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.is_active == True
        ).count()
        
        answered_count = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).count()
        
        completed = answered_count >= total_questions if total_questions > 0 else False
        
        # Calculate completion percentage
        completion_percentage = (answered_count / total_questions * 100) if total_questions > 0 else 0
        
        # Get the latest answer timestamp as completed_at
        latest_answer = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).order_by(UserQuestionnaireAnswer.answered_at.desc()).first()
        
        completed_at = latest_answer.answered_at.isoformat() if latest_answer and completed else None
        
        return {
            "user_id": user_id,
            "answered_questions": answered_count,
            "total_questions": total_questions,
            "completed": completed,
            "completion_percentage": round(completion_percentage, 1),
            "completed_at": completed_at
        }
