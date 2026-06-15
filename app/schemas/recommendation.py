from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, List, Any


class QuestionnaireAnswersSubmit(BaseModel):
    """Direct map of machine_key to answer_scale value (no wrapper object)"""
    age_group: Optional[int] = Field(None, description="Age group selection (1-4)", example=2)
    occupation_status: Optional[int] = Field(None, description="Occupation status (1-4)", example=1)
    study_or_work_field: Optional[int] = Field(None, description="Study or work field (1-5)", example=3)
    busiest_time: Optional[int] = Field(None, description="Busiest time of day (1-5)", example=2)
    sleep_time: Optional[int] = Field(None, description="Sleep time (1-4)", example=3)
    first_activity_home: Optional[int] = Field(None, description="First activity when home (1-4)", example=2)
    mess_tolerance: Optional[int] = Field(None, description="Mess tolerance (1-4)", example=3)
    free_day_style: Optional[int] = Field(None, description="Free day style (1-4)", example=2)
    group_activity_preference: Optional[int] = Field(None, description="Group activity preference (1-4)", example=3)
    study_environment: Optional[int] = Field(None, description="Study environment preference (1-4)", example=2)
    smoking_preference: Optional[int] = Field(None, description="Smoking preference (1-4)", example=1)
    biggest_shared_living_issue: Optional[int] = Field(None, description="Biggest shared living issue (1-4)", example=2)
    flexibility_level: Optional[int] = Field(None, description="Flexibility level (1-4)", example=3)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "age_group": 2,
                    "occupation_status": 1,
                    "study_or_work_field": 3,
                    "busiest_time": 2,
                    "sleep_time": 3,
                    "first_activity_home": 2,
                    "mess_tolerance": 3,
                    "free_day_style": 2,
                    "group_activity_preference": 3,
                    "study_environment": 2,
                    "smoking_preference": 1,
                    "biggest_shared_living_issue": 2,
                    "flexibility_level": 3
                }
            ]
        }
    )

    @field_validator('*')
    @classmethod
    def validate_answer_scale(cls, v):
        """Validate that answer scale is a positive integer."""
        if v is not None:
            if not isinstance(v, int) or v < 1:
                raise ValueError("Answer scale must be a positive integer (>= 1)")
        return v


class QuestionOption(BaseModel):
    """Single question option."""
    value: int = Field(..., description="Option value (1-based index)", example=1)
    label: str = Field(..., description="Option label text", example="18-24")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "value": 1,
                    "label": "18-24"
                }
            ]
        }
    )


class Question(BaseModel):
    """Single questionnaire question."""
    id: int = Field(..., description="Question ID", example=1)
    machine_key: str = Field(..., description="Machine-readable key for the question", example="age_group")
    question_text: str = Field(..., description="Question text displayed to user", example="What is your age group?")
    category: str = Field(..., description="Question category", example="demographics")
    options: Dict[str, QuestionOption] = Field(..., description="Map of option key to option details")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "machine_key": "age_group",
                    "question_text": "What is your age group?",
                    "category": "demographics",
                    "options": {
                        "option_1": {"value": 1, "label": "18-24"},
                        "option_2": {"value": 2, "label": "25-34"},
                        "option_3": {"value": 3, "label": "35-44"},
                        "option_4": {"value": 4, "label": "45+"}
                    }
                }
            ]
        }
    )


class QuestionnaireQuestionsResponse(BaseModel):
    """Response containing all questionnaire questions."""
    questions: List[Question] = Field(..., description="List of all questionnaire questions")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "machine_key": "age_group",
                            "question_text": "What is your age group?",
                            "category": "demographics",
                            "options": {
                                "option_1": {"value": 1, "label": "18-24"},
                                "option_2": {"value": 2, "label": "25-34"},
                                "option_3": {"value": 3, "label": "35-44"},
                                "option_4": {"value": 4, "label": "45+"}
                            }
                        }
                    ]
                }
            ]
        }
    )


class QuestionnaireStatusResponse(BaseModel):
    """Questionnaire completion status for a user."""
    user_id: str = Field(..., description="User ID", example="63a0c0e9-1aa2-415b-81c5-2338ea8fb559")
    answered_questions: int = Field(..., description="Number of answered questions", example=5)
    total_questions: int = Field(..., description="Total number of questions", example=13)
    completed: bool = Field(..., description="Whether questionnaire is completed", example=False)
    completion_percentage: int = Field(..., description="Completion percentage (0-100)", example=38)
    missing_question_ids: List[int] = Field(..., description="IDs of unanswered questions", example=[6, 7, 8, 9, 10, 11, 12, 13])
    next_question_id: Optional[int] = Field(None, description="Next question ID to answer", example=6)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answered_questions": 5,
                    "total_questions": 13,
                    "completed": False,
                    "completion_percentage": 38,
                    "missing_question_ids": [6, 7, 8, 9, 10, 11, 12, 13],
                    "next_question_id": 6
                }
            ]
        }
    )


class QuestionnaireAnswersSubmitResponse(BaseModel):
    """Response after submitting questionnaire answers."""
    status: str = Field(..., description="Operation status", example="ok")
    user_id: str = Field(..., description="User ID", example="63a0c0e9-1aa2-415b-81c5-2338ea8fb559")
    answers_count: int = Field(..., description="Number of answers submitted", example=13)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answers_count": 13
                }
            ]
        }
    )


class RoomMatch(BaseModel):
    """Room-level compatibility match."""
    room_id: int = Field(..., description="Room ID", example=123)
    room_match_score: float = Field(..., description="Room compatibility score (0-100)", example=85.5)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "room_id": 123,
                    "room_match_score": 85.5
                }
            ]
        }
    )


class PropertyMatchResponse(BaseModel):
    """Property and room compatibility scores."""
    property_id: int = Field(..., description="Property ID", example=456)
    property_match_score: float = Field(..., description="Property compatibility score (0-100)", example=78.2)
    rooms: List[RoomMatch] = Field(..., description="List of room matches within the property")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "property_id": 456,
                    "property_match_score": 78.2,
                    "rooms": [
                        {"room_id": 123, "room_match_score": 85.5},
                        {"room_id": 124, "room_match_score": 72.3}
                    ]
                }
            ]
        }
    )


class PropertyMatchScore(BaseModel):
    """Property match score for shared properties endpoint."""
    property_id: int = Field(..., description="Property ID", example=456)
    property_match_score: float = Field(..., description="Property compatibility score (0-100)", example=78.2)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "property_id": 456,
                    "property_match_score": 78.2
                }
            ]
        }
    )


class SharedPropertiesMatchResponse(BaseModel):
    """Response for shared properties match scores."""
    matches: List[PropertyMatchScore] = Field(..., description="List of property match scores")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "matches": [
                        {"property_id": 456, "property_match_score": 78.2},
                        {"property_id": 457, "property_match_score": 65.4},
                        {"property_id": 458, "property_match_score": 82.1}
                    ]
                }
            ]
        }
    )


class AdminUserWithAnswers(BaseModel):
    """Admin view of user with questionnaire answers."""
    user_profile_id: int = Field(..., description="Internal user profile ID", example=1)
    external_user_id: str = Field(..., description="External user ID from auth system", example="63a0c0e9-1aa2-415b-81c5-2338ea8fb559")
    answers_count: int = Field(..., description="Number of questionnaire answers", example=13)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_profile_id": 1,
                    "external_user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answers_count": 13
                }
            ]
        }
    )


class AdminUsersListResponse(BaseModel):
    """Response for admin endpoint listing users with answers."""
    users: List[AdminUserWithAnswers] = Field(..., description="List of users with questionnaire answers")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "users": [
                        {
                            "user_profile_id": 1,
                            "external_user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                            "answers_count": 13
                        },
                        {
                            "user_profile_id": 2,
                            "external_user_id": "74b1d1f0-2bb3-526c-92d6-3449fb9gc660",
                            "answers_count": 8
                        }
                    ]
                }
            ]
        }
    )


class AdminUserAnswersResponse(BaseModel):
    """Admin response for user questionnaire answers."""
    user_id: str = Field(..., description="User ID", example="63a0c0e9-1aa2-415b-81c5-2338ea8fb559")
    answers: Dict[str, int] = Field(..., description="Map of machine_key to answer_scale", example={"age_group": 2, "occupation_status": 1})

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
                    "answers": {
                        "age_group": 2,
                        "occupation_status": 1,
                        "study_or_work_field": 3,
                        "busiest_time": 2,
                        "sleep_time": 3,
                        "first_activity_home": 2,
                        "mess_tolerance": 3,
                        "free_day_style": 2,
                        "group_activity_preference": 3,
                        "study_environment": 2,
                        "smoking_preference": 1,
                        "biggest_shared_living_issue": 2,
                        "flexibility_level": 3
                    }
                }
            ]
        }
    )


class AdminUpsertResponse(BaseModel):
    """Response for admin upsert operation."""
    status: str = Field(..., description="Operation status", example="success")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "success"
                }
            ]
        }
    )


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall system status", example="healthy")
    database: str = Field(..., description="Database connection status", example="connected")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "healthy",
                    "database": "connected"
                }
            ]
        }
    )