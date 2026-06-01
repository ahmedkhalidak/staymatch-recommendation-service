"""Unit tests for Pydantic schemas — validation."""
import pytest
from pydantic import ValidationError
from app.schemas.recommendation import (
    UserProfileCreate, InteractionCreate, QuestionnaireAnswersSubmit, AnswerSubmit
)

class TestUserProfileCreate:
    def test_valid_profile(self):
        profile = UserProfileCreate(user_id="user_123", full_name="Ahmed",
                                     gender="male", occupation="student")
        assert profile.user_id == "user_123"
        assert profile.full_name == "Ahmed"

    def test_minimal_profile(self):
        """Only user_id is required"""
        profile = UserProfileCreate(user_id="user_123")
        assert profile.user_id == "user_123"

    def test_invalid_no_user_id(self):
        """user_id is required"""
        with pytest.raises(ValidationError):
            UserProfileCreate()

class TestInteractionCreate:
    def test_valid_interaction(self):
        interaction = InteractionCreate(user_id="u1", target_type="property",
                                         target_id=1, action="viewed")
        assert interaction.action == "viewed"

    def test_with_dwell_time(self):
        interaction = InteractionCreate(user_id="u1", target_type="property",
                                         target_id=1, action="viewed",
                                         dwell_seconds=30)
        assert interaction.dwell_seconds == 30

    def test_with_location(self):
        interaction = InteractionCreate(user_id="u1", target_type="search",
                                         target_id=0, action="searched",
                                         search_lat=30.04, search_lng=31.24)
        assert interaction.search_lat == 30.04

class TestQuestionnaireAnswersSubmit:
    def test_single_answer(self):
        data = QuestionnaireAnswersSubmit(answers=[AnswerSubmit(question_id=1, answer_value="yes")])
        assert len(data.answers) == 1
        assert data.answers[0].answer_value == "yes"

    def test_multiple_answers(self):
        data = QuestionnaireAnswersSubmit(answers=[
            AnswerSubmit(question_id=1, answer_value="male"),
            AnswerSubmit(question_id=2, answer_value="student", answer_scale=3),
        ])
        assert len(data.answers) == 2
        assert data.answers[1].answer_scale == 3
