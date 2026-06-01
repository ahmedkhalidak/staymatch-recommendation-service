from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class UserProfileCreate(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    external_user_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    created_at: Optional[datetime] = None


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


class RecommendationResponse(BaseModel):
    id: int
    score: float
    score_breakdown: Optional[dict] = None
    rank: Optional[int] = None


class PropertyRecommendationResponse(RecommendationResponse):
    property_id: int


class RoomRecommendationResponse(RecommendationResponse):
    room_id: int


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


class SyncStatusResponse(BaseModel):
    last_sync: Optional[datetime] = None
    tables: dict[str, Any] = {}


class MatchComputeResponse(BaseModel):
    seeker_user_id: str
    matches: list[dict]


class MatchResultResponse(BaseModel):
    seeker_user_id: str
    room_id: int
    property_id: int
    room_compatibility_score: float
    created_at: Optional[datetime] = None