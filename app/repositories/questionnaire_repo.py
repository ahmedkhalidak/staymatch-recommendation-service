"""Questionnaire repository for managing questionnaire data."""
from sqlalchemy.orm import joinedload

from app.database.session import get_session
from app.database.models.user import (
    QuestionnaireCategory,
    QuestionnaireQuestion,
    UserQuestionnaireAnswer,
    UserProfile,
    UserSearchPreference,
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

    def _resolve_user_profile_id(self, external_user_id: str) -> str:
        """Resolve external user ID to user_profile_id."""
        profile = self.session.query(UserProfile).filter(
            UserProfile.external_user_id == external_user_id
        ).first()
        return str(profile.id) if profile else None

    def save_answers(self, external_user_id: str, answers: list[dict]):
        """Save or update questionnaire answers for a user."""
        user_profile_id = self._resolve_user_profile_id(external_user_id)
        if not user_profile_id:
            raise ValueError(f"User profile not found for external_user_id: {external_user_id}")
        
        question_ids = [a["question_id"] for a in answers]
        existing_answers = {
            a.question_id: a
            for a in self.session.query(UserQuestionnaireAnswer).filter(
                UserQuestionnaireAnswer.user_profile_id == user_profile_id,
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
                    user_profile_id=user_profile_id,
                    question_id=answer["question_id"],
                    answer_value=answer["answer_value"],
                    answer_scale=answer.get("answer_scale")
                ))
        self.session.commit()

    def get_answers(self, external_user_id: str):
        """Get all questionnaire answers for a user."""
        user_profile_id = self._resolve_user_profile_id(external_user_id)
        if not user_profile_id:
            return []
        return self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_profile_id == user_profile_id
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

    def get_questionnaire_status(self, external_user_id: str) -> dict:
        """Get questionnaire completion status for a user by counting answers."""
        user_profile_id = self._resolve_user_profile_id(external_user_id)
        if not user_profile_id:
            return {
                "user_id": external_user_id,
                "answered_questions": 0,
                "total_questions": 0,
                "completed": False,
                "completion_percentage": 0,
                "completed_at": None,
                "missing_question_ids": [],
                "next_question_id": None
            }
        
        total_questions = self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.is_active == True
        ).all()
        
        answered_count = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_profile_id == user_profile_id
        ).count()
        
        completed = answered_count >= len(total_questions) if total_questions else False
        
        # Calculate completion percentage
        completion_percentage = int((answered_count / len(total_questions) * 100)) if total_questions else 0
        
        # Get missing question IDs
        answered_question_ids = set(
            a.question_id for a in self.session.query(UserQuestionnaireAnswer).filter(
                UserQuestionnaireAnswer.user_profile_id == user_profile_id
            ).all()
        )
        all_question_ids = {q.id for q in total_questions}
        missing_question_ids = sorted(list(all_question_ids - answered_question_ids))
        
        # Get next question ID (first missing by sort order)
        next_question_id = None
        if missing_question_ids:
            next_question = min(
                (q for q in total_questions if q.id in missing_question_ids),
                key=lambda q: q.sort_order
            )
            next_question_id = next_question.id if next_question else None
        
        # Get the latest answer timestamp as completed_at
        latest_answer = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_profile_id == user_profile_id
        ).order_by(UserQuestionnaireAnswer.answered_at.desc()).first()
        
        completed_at = latest_answer.answered_at.isoformat() if latest_answer and completed else None
        
        return {
            "user_id": external_user_id,
            "answered_questions": answered_count,
            "total_questions": len(total_questions),
            "completed": completed,
            "completion_percentage": round(completion_percentage, 1),
            "completed_at": completed_at,
            "missing_question_ids": missing_question_ids,
            "next_question_id": next_question_id
        }

    def get_search_preferences(self, external_user_id: str):
        """Get user search preferences by external_user_id."""
        user_profile_id = self._resolve_user_profile_id(external_user_id)
        if not user_profile_id:
            return None
        return self.session.query(UserSearchPreference).filter(
            UserSearchPreference.user_profile_id == user_profile_id
        ).first()

    def get_all_active_questions(self):
        """Get all active questions ordered by sort_order."""
        return self.session.query(QuestionnaireQuestion).filter(
            QuestionnaireQuestion.is_active == True
        ).order_by(QuestionnaireQuestion.sort_order).all()
