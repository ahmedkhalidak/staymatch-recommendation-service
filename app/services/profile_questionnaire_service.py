"""Service for Profile Questionnaire API mapping logic."""
from typing import Optional, Dict, List
from datetime import datetime

from app.repositories.questionnaire_repo import QuestionnaireRepository
from app.services.property_api_client import PropertyAPIClient
from app.schemas.profile import (
    ProfileQuestionnaireResponse,
    CompatibilityPreferences,
    VibeCheck,
    CleanlinessLevel,
    CulturalImportance,
    HousingPreferences,
)


class ProfileQuestionnaireService:
    """Service for transforming questionnaire answers into UI-friendly profile data."""

    def __init__(self):
        self.repo = QuestionnaireRepository()
        self.api_client = PropertyAPIClient()

        # Question ID mappings
        self.SMOKING_QUESTION_ID = 11  # smoking_preference
        self.SLEEP_QUESTION_ID = 5  # sleep_time
        self.MESS_QUESTION_ID = 7  # mess_tolerance
        self.GROUP_QUESTION_ID = 9  # group_activity_preference

        # Smoker mapping: 1,2 -> false (non-smoker), 3,4 -> true (smoker)
        self.SMOKER_FALSE_VALUES = {1, 2}
        self.SMOKER_TRUE_VALUES = {3, 4}

        # Night owl mapping: 3,4 -> true (12AM-2AM, After 2AM)
        self.NIGHT_OWL_TRUE_VALUES = {3, 4}

        # Cleanliness level labels
        self.CLEANLINESS_LABELS = {
            1: "Very Strict",
            2: "Strict",
            3: "Moderate",
            4: "Relaxed",
        }

        # Cultural importance labels
        self.CULTURAL_LABELS = {
            1: "High",
            2: "Medium",
            3: "Low",
            4: "Very Low",
        }

    async def get_profile_questionnaire(self, external_user_id: str) -> ProfileQuestionnaireResponse:
        """Get complete profile questionnaire data for a user."""
        # Get questionnaire answers
        answers = self.repo.get_answers(external_user_id)
        answers_map = {a.question_id: a.answer_scale for a in answers}

        # Get all active questions to calculate missing questions
        all_questions = self.repo.get_all_active_questions()
        total_questions = len(all_questions)
        answered_questions = len(answers_map)

        # Calculate completion percentage
        completion_percentage = int((answered_questions / total_questions * 100)) if total_questions > 0 else 0

        # Determine completion status
        completed = answered_questions == total_questions
        needs_questionnaire = not completed

        # Get missing question IDs
        answered_question_ids = set(answers_map.keys())
        all_question_ids = {q.id for q in all_questions}
        missing_question_ids = sorted(list(all_question_ids - answered_question_ids))

        # Get next question ID (first missing by sort order)
        next_question_id = missing_question_ids[0] if missing_question_ids else None

        # Get last updated timestamp
        last_updated = self._get_last_updated(answers)

        # Fetch about_me from .NET API
        about_me = await self._fetch_about_me(external_user_id)

        # Build compatibility preferences
        compatibility_preferences = self._build_compatibility_preferences(answers_map)

        # Build housing preferences
        housing_preferences = self._build_housing_preferences(external_user_id)

        # Build vibe check
        vibe_check = self._build_vibe_check(answers_map)

        return ProfileQuestionnaireResponse(
            completed=completed,
            can_match=True,
            can_edit=True,
            needs_questionnaire=needs_questionnaire,
            answered_questions=answered_questions,
            total_questions=total_questions,
            completion_percentage=completion_percentage,
            missing_question_ids=missing_question_ids,
            next_question_id=next_question_id,
            last_updated=last_updated,
            about_me=about_me,
            compatibility_preferences=compatibility_preferences,
            housing_preferences=housing_preferences,
            vibe_check=vibe_check,
        )

    def _get_last_updated(self, answers: List) -> Optional[str]:
        """Get the last updated timestamp from answers."""
        if not answers:
            return None
        latest = max(answers, key=lambda a: a.answered_at)
        return latest.answered_at.isoformat() if latest.answered_at else None

    async def _fetch_about_me(self, external_user_id: str) -> Optional[str]:
        """Fetch about_me from .NET User Profile API."""
        try:
            # Use the existing PropertyAPIClient to fetch user profile
            # The API expects the external_user_id (GUID from .NET)
            profile_data = await self.api_client.get_user_profile(external_user_id)
            if profile_data and "aboutMe" in profile_data:
                return profile_data["aboutMe"]
            return None
        except Exception:
            # If API call fails, return None
            return None

    def _build_compatibility_preferences(self, answers_map: Dict[int, int]) -> CompatibilityPreferences:
        """Build compatibility preferences from questionnaire answers."""
        # Smoker preference (Q11)
        smoker_answer = answers_map.get(self.SMOKING_QUESTION_ID)
        if smoker_answer in self.SMOKER_FALSE_VALUES:
            smoker = False
        elif smoker_answer in self.SMOKER_TRUE_VALUES:
            smoker = True
        else:
            smoker = None

        # Night owl (Q5)
        sleep_answer = answers_map.get(self.SLEEP_QUESTION_ID)
        if sleep_answer in self.NIGHT_OWL_TRUE_VALUES:
            night_owl = True
        elif sleep_answer is not None:
            night_owl = False
        else:
            night_owl = None

        # Has pets (not implemented yet)
        has_pets = None

        return CompatibilityPreferences(
            smoker=smoker,
            has_pets=has_pets,
            night_owl=night_owl,
        )

    def _build_housing_preferences(self, external_user_id: str) -> HousingPreferences:
        """Build housing preferences from user search preferences."""
        search_pref = self.repo.get_search_preferences(external_user_id)
        if not search_pref:
            return HousingPreferences(governorate=None, budget=None)

        # Use preferred_government as governorate
        governorate = search_pref.preferred_government

        # Calculate budget as average of min and max
        if search_pref.min_budget is not None and search_pref.max_budget is not None:
            budget = (search_pref.min_budget + search_pref.max_budget) // 2
        elif search_pref.min_budget is not None:
            budget = search_pref.min_budget
        elif search_pref.max_budget is not None:
            budget = search_pref.max_budget
        else:
            budget = None

        return HousingPreferences(
            governorate=governorate,
            budget=budget,
        )

    def _build_vibe_check(self, answers_map: Dict[int, int]) -> VibeCheck:
        """Build vibe check preferences from questionnaire answers."""
        # Cleanliness level (Q7 - mess_tolerance)
        mess_answer = answers_map.get(self.MESS_QUESTION_ID)
        if mess_answer is not None:
            cleanliness_level = CleanlinessLevel(
                value=mess_answer,
                label=self.CLEANLINESS_LABELS.get(mess_answer, "Unknown"),
            )
        else:
            cleanliness_level = None

        # Cultural importance (Q9 - group_activity_preference)
        group_answer = answers_map.get(self.GROUP_QUESTION_ID)
        if group_answer is not None:
            cultural_importance = CulturalImportance(
                value=group_answer,
                label=self.CULTURAL_LABELS.get(group_answer, "Unknown"),
            )
        else:
            cultural_importance = None

        return VibeCheck(
            cleanliness_level=cleanliness_level,
            cultural_importance=cultural_importance,
        )
