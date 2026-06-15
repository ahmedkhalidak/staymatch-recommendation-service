from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database.models.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_user_id = Column(UUID(as_uuid=True))
    external_user_id = Column(String(255), unique=True)
    full_name = Column(Text)
    phone = Column(String(50))
    gender = Column(String(20))
    birth_year = Column(Integer)
    nationality = Column(String(100))
    occupation = Column(String(100))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())


Index("idx_user_profiles_auth", UserProfile.auth_user_id)
Index("idx_user_profiles_external", UserProfile.external_user_id)


class QuestionnaireCategory(Base):
    __tablename__ = "questionnaire_categories"

    id = Column(Integer, primary_key=True)
    name_ar = Column(Text, nullable=False)
    name_en = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)

    questions = relationship("QuestionnaireQuestion", back_populates="category", order_by="QuestionnaireQuestion.sort_order")


class QuestionnaireQuestion(Base):
    __tablename__ = "questionnaire_questions"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("questionnaire_categories.id"))
    question_ar = Column(Text, nullable=False)
    question_en = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False)
    options_ar = Column(JSONB)
    options_en = Column(JSONB)
    weight = Column(Float, default=1.0)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    category = relationship("QuestionnaireCategory", back_populates="questions")
    answers = relationship("UserQuestionnaireAnswer", back_populates="question")


class UserQuestionnaireAnswer(Base):
    __tablename__ = "user_questionnaire_answers"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    question_id = Column(Integer, ForeignKey("questionnaire_questions.id"), nullable=False)
    answer_value = Column(Text, nullable=False)
    answer_scale = Column(Integer)
    answered_at = Column(DateTime, server_default=func.current_timestamp())

    question = relationship("QuestionnaireQuestion", back_populates="answers")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id"),
    )


Index("idx_answers_user", UserQuestionnaireAnswer.user_id)
Index("idx_answers_question", UserQuestionnaireAnswer.question_id)


class UserSearchPreference(Base):
    __tablename__ = "user_search_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, unique=True)
    min_budget = Column(Integer)
    max_budget = Column(Integer)
    preferred_city = Column(Text)
    preferred_government = Column(Text)
    preferred_property_type = Column(String(20))
    furnished = Column(Boolean)
    wifi = Column(Boolean)
    air_conditioning = Column(Boolean)
    balcony = Column(Boolean)
    private_bathroom = Column(Boolean)
    tenant_type = Column(String(20))
    gender_preference = Column(String(20))
    shared_room = Column(Boolean)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())