from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict


class QuestionnaireAnswersSubmit(BaseModel):
    """Direct map of machine_key to answer_scale value (no wrapper object)"""
    age_group: Optional[int] = Field(None, description="Age group selection (1-4)")
    occupation_status: Optional[int] = Field(None, description="Occupation status (1-4)")
    study_or_work_field: Optional[int] = Field(None, description="Study or work field (1-5)")
    busiest_time: Optional[int] = Field(None, description="Busiest time of day (1-5)")
    sleep_time: Optional[int] = Field(None, description="Sleep time (1-4)")
    first_activity_home: Optional[int] = Field(None, description="First activity when home (1-4)")
    mess_tolerance: Optional[int] = Field(None, description="Mess tolerance (1-4)")
    free_day_style: Optional[int] = Field(None, description="Free day style (1-4)")
    group_activity_preference: Optional[int] = Field(None, description="Group activity preference (1-4)")
    study_environment: Optional[int] = Field(None, description="Study environment preference (1-4)")
    smoking_preference: Optional[int] = Field(None, description="Smoking preference (1-4)")
    biggest_shared_living_issue: Optional[int] = Field(None, description="Biggest shared living issue (1-4)")
    flexibility_level: Optional[int] = Field(None, description="Flexibility level (1-4)")
    
    @field_validator('*')
    @classmethod
    def validate_answer_scale(cls, v):
        """Validate that answer scale is a positive integer."""
        if v is not None:
            if not isinstance(v, int) or v < 1:
                raise ValueError("Answer scale must be a positive integer (>= 1)")
        return v