"""Unit tests for Profile Questionnaire API service."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.profile_questionnaire_service import ProfileQuestionnaireService
from app.schemas.profile import (
    ProfileQuestionnaireResponse,
    CompatibilityPreferences,
    VibeCheck,
    CleanlinessLevel,
    CulturalImportance,
    HousingPreferences,
)


class MockQuestionnaireAnswer:
    def __init__(self, question_id, answer_scale, answered_at=None):
        self.question_id = question_id
        self.answer_scale = answer_scale
        self.answered_at = answered_at or datetime.now()


class MockQuestionnaireQuestion:
    def __init__(self, id, sort_order):
        self.id = id
        self.sort_order = sort_order


class MockUserSearchPreference:
    def __init__(self, **kwargs):
        # Set default values for all expected attributes
        self.preferred_government = None
        self.preferred_city = None
        self.min_budget = None
        self.max_budget = None
        self.preferred_property_type = None
        self.furnished = None
        self.wifi = None
        self.air_conditioning = None
        self.balcony = None
        self.private_bathroom = None
        self.tenant_type = None
        self.gender_preference = None
        self.shared_room = None
        
        # Override with provided kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestProfileQuestionnaireService:
    @pytest.fixture
    def service(self):
        return ProfileQuestionnaireService()

    @pytest.fixture
    def mock_repo(self, service):
        service.repo = MagicMock()
        return service.repo

    @pytest.fixture
    def mock_api_client(self, service):
        service.api_client = MagicMock()
        return service.api_client

    @pytest.mark.asyncio
    async def test_no_answers(self, service, mock_repo, mock_api_client):
        """Test user with no questionnaire answers."""
        external_user_id = "user-123"
        
        # Mock repository responses
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [
            MockQuestionnaireQuestion(1, 1),
            MockQuestionnaireQuestion(2, 2),
            MockQuestionnaireQuestion(3, 3),
        ]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        # Execute
        result = await service.get_profile_questionnaire(external_user_id)
        
        # Verify basic status
        assert result.completed is False
        assert result.can_match is True
        assert result.can_edit is True
        assert result.needs_questionnaire is True
        assert result.answered_questions == 0
        assert result.total_questions == 3
        assert result.completion_percentage == 0
        assert result.missing_question_ids == [1, 2, 3]
        assert result.next_question_id == 1
        assert result.about_me is None
        
        # Verify preferences are null when no answers
        assert result.compatibility_preferences.smoker is None
        assert result.compatibility_preferences.has_pets is None
        assert result.compatibility_preferences.night_owl is None
        assert result.vibe_check.cleanliness_level is None
        assert result.vibe_check.cultural_importance is None
        
        # Verify housing preferences are null when no search preferences
        assert result.housing_preferences.governorate is None
        assert result.housing_preferences.budget is None

    @pytest.mark.asyncio
    async def test_partial_answers(self, service, mock_repo, mock_api_client):
        """Test user with partial questionnaire answers."""
        external_user_id = "user-456"
        
        # Mock repository responses
        mock_repo.get_answers.return_value = [
            MockQuestionnaireAnswer(5, 3),  # sleep_time - night owl
            MockQuestionnaireAnswer(7, 1),  # mess_tolerance - very strict
        ]
        mock_repo.get_all_active_questions.return_value = [
            MockQuestionnaireQuestion(1, 1),
            MockQuestionnaireQuestion(5, 2),
            MockQuestionnaireQuestion(7, 3),
            MockQuestionnaireQuestion(9, 4),
        ]
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            preferred_government="Cairo",
            min_budget=1000,
            max_budget=2000,
        )
        mock_api_client.get_user_profile = AsyncMock(return_value={"aboutMe": "I love coding"})
        
        # Execute
        result = await service.get_profile_questionnaire(external_user_id)
        
        # Verify basic status
        assert result.completed is False
        assert result.can_match is True
        assert result.can_edit is True
        assert result.needs_questionnaire is True
        assert result.answered_questions == 2
        assert result.total_questions == 4
        assert result.completion_percentage == 50
        assert result.missing_question_ids == [1, 9]
        assert result.next_question_id == 1
        assert result.about_me == "I love coding"
        
        # Verify compatibility preferences
        assert result.compatibility_preferences.smoker is None  # Q11 not answered
        assert result.compatibility_preferences.has_pets is None
        assert result.compatibility_preferences.night_owl is True  # Q5 = 3
        
        # Verify vibe check
        assert result.vibe_check.cleanliness_level.value == 1  # Q7 = 1
        assert result.vibe_check.cleanliness_level.label == "Very Strict"
        assert result.vibe_check.cultural_importance is None  # Q9 not answered
        
        # Verify housing preferences
        assert result.housing_preferences.governorate == "Cairo"
        assert result.housing_preferences.budget == 1500  # average of 1000 and 2000

    @pytest.mark.asyncio
    async def test_completed_answers(self, service, mock_repo, mock_api_client):
        """Test user with all questionnaire answers completed."""
        external_user_id = "user-789"
        
        # Mock repository responses - all 13 questions answered
        answers = [
            MockQuestionnaireAnswer(1, 1),
            MockQuestionnaireAnswer(2, 2),
            MockQuestionnaireAnswer(3, 3),
            MockQuestionnaireAnswer(4, 1),
            MockQuestionnaireAnswer(5, 2),  # sleep_time - not night owl
            MockQuestionnaireAnswer(6, 1),
            MockQuestionnaireAnswer(7, 3),  # mess_tolerance - moderate
            MockQuestionnaireAnswer(8, 2),
            MockQuestionnaireAnswer(9, 2),  # group_activity - medium
            MockQuestionnaireAnswer(10, 1),
            MockQuestionnaireAnswer(11, 1),  # smoking - non-smoker
            MockQuestionnaireAnswer(12, 1),
            MockQuestionnaireAnswer(13, 1),
        ]
        mock_repo.get_answers.return_value = answers
        mock_repo.get_all_active_questions.return_value = [
            MockQuestionnaireQuestion(i, i) for i in range(1, 14)
        ]
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            preferred_government="Alexandria",
            min_budget=3000,
            max_budget=5000,
        )
        mock_api_client.get_user_profile = AsyncMock(return_value={"aboutMe": "Software engineer"})
        
        # Execute
        result = await service.get_profile_questionnaire(external_user_id)
        
        # Verify basic status
        assert result.completed is True
        assert result.can_match is True
        assert result.can_edit is True
        assert result.needs_questionnaire is False
        assert result.answered_questions == 13
        assert result.total_questions == 13
        assert result.completion_percentage == 100
        assert result.missing_question_ids == []
        assert result.next_question_id is None
        assert result.about_me == "Software engineer"
        
        # Verify compatibility preferences
        assert result.compatibility_preferences.smoker is False  # Q11 = 1 (non-smoker)
        assert result.compatibility_preferences.has_pets is None
        assert result.compatibility_preferences.night_owl is False  # Q5 = 2 (not night owl)
        
        # Verify vibe check
        assert result.vibe_check.cleanliness_level.value == 3  # Q7 = 3
        assert result.vibe_check.cleanliness_level.label == "Moderate"
        assert result.vibe_check.cultural_importance.value == 2  # Q9 = 2
        assert result.vibe_check.cultural_importance.label == "Medium"
        
        # Verify housing preferences
        assert result.housing_preferences.governorate == "Alexandria"
        assert result.housing_preferences.budget == 4000  # average of 3000 and 5000

    @pytest.mark.asyncio
    async def test_smoker_mapping(self, service, mock_repo, mock_api_client):
        """Test smoker preference mapping."""
        external_user_id = "user-smoker"
        
        # Test smoker = true (values 3, 4)
        mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(11, 3)]
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(11, 11)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.compatibility_preferences.smoker is True
        
        # Test smoker = false (values 1, 2)
        mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(11, 2)]
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.compatibility_preferences.smoker is False

    @pytest.mark.asyncio
    async def test_night_owl_mapping(self, service, mock_repo, mock_api_client):
        """Test night owl mapping."""
        external_user_id = "user-nightowl"
        
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(5, 5)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        # Test night owl = true (values 3, 4)
        mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(5, 3)]
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.compatibility_preferences.night_owl is True
        
        # Test night owl = false (other values)
        mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(5, 2)]
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.compatibility_preferences.night_owl is False

    @pytest.mark.asyncio
    async def test_cleanliness_labels(self, service, mock_repo, mock_api_client):
        """Test cleanliness level label mapping."""
        external_user_id = "user-clean"
        
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(7, 7)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        # Test all labels
        labels = {
            1: "Very Strict",
            2: "Strict",
            3: "Moderate",
            4: "Relaxed",
        }
        
        for value, expected_label in labels.items():
            mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(7, value)]
            result = await service.get_profile_questionnaire(external_user_id)
            assert result.vibe_check.cleanliness_level.value == value
            assert result.vibe_check.cleanliness_level.label == expected_label

    @pytest.mark.asyncio
    async def test_cultural_labels(self, service, mock_repo, mock_api_client):
        """Test cultural importance label mapping."""
        external_user_id = "user-cultural"
        
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(9, 9)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        # Test all labels
        labels = {
            1: "High",
            2: "Medium",
            3: "Low",
            4: "Very Low",
        }
        
        for value, expected_label in labels.items():
            mock_repo.get_answers.return_value = [MockQuestionnaireAnswer(9, value)]
            result = await service.get_profile_questionnaire(external_user_id)
            assert result.vibe_check.cultural_importance.value == value
            assert result.vibe_check.cultural_importance.label == expected_label

    @pytest.mark.asyncio
    async def test_missing_search_preferences(self, service, mock_repo, mock_api_client):
        """Test when user has no search preferences."""
        external_user_id = "user-no-prefs"
        
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(1, 1)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        result = await service.get_profile_questionnaire(external_user_id)
        
        assert result.housing_preferences.governorate is None
        assert result.housing_preferences.budget is None

    @pytest.mark.asyncio
    async def test_missing_about_me(self, service, mock_repo, mock_api_client):
        """Test when .NET API returns no about_me."""
        external_user_id = "user-no-about"
        
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(1, 1)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        result = await service.get_profile_questionnaire(external_user_id)
        
        assert result.about_me is None

    @pytest.mark.asyncio
    async def test_about_me_from_api(self, service, mock_repo, mock_api_client):
        """Test fetching about_me from .NET API."""
        external_user_id = "user-with-about"
        
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(1, 1)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value={"aboutMe": "Test bio"})
        
        result = await service.get_profile_questionnaire(external_user_id)
        
        assert result.about_me == "Test bio"

    @pytest.mark.asyncio
    async def test_budget_calculation(self, service, mock_repo, mock_api_client):
        """Test budget calculation from min and max."""
        external_user_id = "user-budget"
        
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(1, 1)]
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        # Test average of min and max
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            min_budget=1000,
            max_budget=3000,
        )
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.housing_preferences.budget == 2000
        
        # Test only min
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            min_budget=1500,
            max_budget=None,
        )
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.housing_preferences.budget == 1500
        
        # Test only max
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            min_budget=None,
            max_budget=2500,
        )
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.housing_preferences.budget == 2500
        
        # Test neither
        mock_repo.get_search_preferences.return_value = MockUserSearchPreference(
            min_budget=None,
            max_budget=None,
        )
        result = await service.get_profile_questionnaire(external_user_id)
        assert result.housing_preferences.budget is None

    @pytest.mark.asyncio
    async def test_last_updated_timestamp(self, service, mock_repo, mock_api_client):
        """Test last_updated timestamp from latest answer."""
        external_user_id = "user-timestamp"
        
        now = datetime.now()
        earlier = datetime(2026, 1, 1)
        
        mock_repo.get_answers.return_value = [
            MockQuestionnaireAnswer(1, 1, answered_at=earlier),
            MockQuestionnaireAnswer(2, 2, answered_at=now),
        ]
        mock_repo.get_all_active_questions.return_value = [
            MockQuestionnaireQuestion(1, 1),
            MockQuestionnaireQuestion(2, 2),
        ]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(return_value=None)
        
        result = await service.get_profile_questionnaire(external_user_id)
        
        assert result.last_updated is not None
        # Should be the latest timestamp
        assert result.last_updated == now.isoformat()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, service, mock_repo, mock_api_client):
        """Test handling of .NET API errors."""
        external_user_id = "user-api-error"
        
        mock_repo.get_answers.return_value = []
        mock_repo.get_all_active_questions.return_value = [MockQuestionnaireQuestion(1, 1)]
        mock_repo.get_search_preferences.return_value = None
        mock_api_client.get_user_profile = AsyncMock(side_effect=Exception("API error"))
        
        result = await service.get_profile_questionnaire(external_user_id)
        
        # Should not crash, just return None for about_me
        assert result.about_me is None
