from pydantic import BaseModel
from typing import Optional


class UserProfileCreate(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    college: Optional[str] = None
    sleep_schedule: Optional[str] = None
    smoking_status: Optional[str] = None
    visitor_frequency: Optional[str] = None


class SearchPreferenceCreate(BaseModel):
    user_id: str
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    preferred_city: Optional[str] = None
    preferred_government: Optional[str] = None
    preferred_property_type: Optional[str] = None
    furnished: Optional[bool] = None
    wifi: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    balcony: Optional[bool] = None
    private_bathroom: Optional[bool] = None
    tenant_type: Optional[str] = None
    gender_preference: Optional[str] = None
    shared_room: Optional[bool] = None


class AnswerSubmit(BaseModel):
    question_id: int
    answer_value: str
    answer_scale: Optional[int] = None


class QuestionnaireAnswersSubmit(BaseModel):
    answers: list[AnswerSubmit]


class InteractionCreate(BaseModel):
    user_id: str
    target_type: str
    target_id: int
    action: str
    context: Optional[dict] = None
    dwell_seconds: Optional[int] = None
    search_lat: Optional[float] = None
    search_lng: Optional[float] = None