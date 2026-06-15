"""Schemas for Profile Questionnaire API."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class CompatibilityPreferences(BaseModel):
    """User compatibility preferences derived from questionnaire answers."""
    smoker: Optional[bool] = Field(None, description="Whether user is a smoker (derived from Q11)", example=False)
    has_pets: Optional[bool] = Field(None, description="Whether user has pets (not implemented yet)", example=None)
    night_owl: Optional[bool] = Field(None, description="Whether user is a night owl (derived from Q5)", example=True)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "smoker": False,
                    "has_pets": None,
                    "night_owl": True
                }
            ]
        }
    )


class CleanlinessLevel(BaseModel):
    """Cleanliness level preference."""
    value: int = Field(..., description="Cleanliness level value (1-4)", example=3)
    label: str = Field(..., description="Cleanliness level label", example="Moderate")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "value": 3,
                    "label": "Moderate"
                }
            ]
        }
    )


class CulturalImportance(BaseModel):
    """Cultural importance preference."""
    value: int = Field(..., description="Cultural importance value (1-4)", example=2)
    label: str = Field(..., description="Cultural importance label", example="Somewhat important")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "value": 2,
                    "label": "Somewhat important"
                }
            ]
        }
    )


class VibeCheck(BaseModel):
    """Vibe check preferences derived from questionnaire answers."""
    cleanliness_level: Optional[CleanlinessLevel] = Field(None, description="Cleanliness level preference (derived from Q7)")
    cultural_importance: Optional[CulturalImportance] = Field(None, description="Cultural importance preference (derived from Q9)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "cleanliness_level": {
                        "value": 3,
                        "label": "Moderate"
                    },
                    "cultural_importance": {
                        "value": 2,
                        "label": "Somewhat important"
                    }
                }
            ]
        }
    )


class HousingPreferences(BaseModel):
    """User housing preferences from search preferences."""
    governorate: Optional[str] = Field(None, description="Preferred governorate", example="Capital")
    budget: Optional[int] = Field(None, description="Average budget (min and max averaged)", example=450)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "governorate": "Capital",
                    "budget": 450
                }
            ]
        }
    )


class ProfileQuestionnaireResponse(BaseModel):
    """Complete profile questionnaire response for the Profile UI."""
    completed: bool = Field(..., description="Whether questionnaire is fully completed", example=True)
    can_match: bool = Field(..., description="Whether user can match (always true)", example=True)
    can_edit: bool = Field(..., description="Whether user can edit preferences (always true)", example=True)
    needs_questionnaire: bool = Field(..., description="Whether user needs to complete questionnaire", example=False)

    answered_questions: int = Field(..., description="Number of answered questions", example=13)
    total_questions: int = Field(..., description="Total number of questions (13)", example=13)

    completion_percentage: int = Field(..., description="Completion percentage (0-100)", example=100)

    missing_question_ids: List[int] = Field(default_factory=list, description="IDs of unanswered questions", example=[])
    next_question_id: Optional[int] = Field(None, description="Next question ID to answer", example=None)

    last_updated: Optional[str] = Field(None, description="Last update timestamp", example="2024-01-15T10:30:00Z")

    about_me: Optional[str] = Field(None, description="About me text from .NET User Profile API", example="Software engineer who enjoys hiking and coffee")

    compatibility_preferences: CompatibilityPreferences = Field(..., description="Compatibility preferences")
    housing_preferences: HousingPreferences = Field(..., description="Housing preferences")
    vibe_check: VibeCheck = Field(..., description="Vibe check preferences")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "completed": True,
                    "can_match": True,
                    "can_edit": True,
                    "needs_questionnaire": False,
                    "answered_questions": 13,
                    "total_questions": 13,
                    "completion_percentage": 100,
                    "missing_question_ids": [],
                    "next_question_id": None,
                    "last_updated": "2024-01-15T10:30:00Z",
                    "about_me": "Software engineer who enjoys hiking and coffee",
                    "compatibility_preferences": {
                        "smoker": False,
                        "has_pets": None,
                        "night_owl": True
                    },
                    "housing_preferences": {
                        "governorate": "Capital",
                        "budget": 450
                    },
                    "vibe_check": {
                        "cleanliness_level": {
                            "value": 3,
                            "label": "Moderate"
                        },
                        "cultural_importance": {
                            "value": 2,
                            "label": "Somewhat important"
                        }
                    }
                }
            ]
        }
    )
