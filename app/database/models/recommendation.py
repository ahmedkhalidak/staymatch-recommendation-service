from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB, DOUBLE_PRECISION
from sqlalchemy.sql import func

from app.database.models.base import Base


class ScoringWeight(Base):
    __tablename__ = "scoring_weights"

    id = Column(Integer, primary_key=True)
    weight_key = Column(String(50), nullable=False)
    weight_value = Column(Float, nullable=False)
    weight_group = Column(String(30), nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, server_default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint("weight_key", "weight_group", name="uq_weight_key_group"),
        Index("idx_weights_group", "weight_group"),
    )


class UserFeedbackWeight(Base):
    __tablename__ = "user_feedback_weights"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    city = Column(Text)
    government = Column(Text)
    property_type = Column(Integer)
    min_budget = Column(Float)
    max_budget = Column(Float)
    boost_factor = Column(Float, default=1.0)
    updated_at = Column(DateTime, server_default=func.current_timestamp())

    __table_args__ = (
        Index("idx_feedback_user", "user_id"),
    )


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False)
    context = Column(JSONB)
    dwell_seconds = Column(Integer)
    search_lat = Column(DOUBLE_PRECISION)
    search_lng = Column(DOUBLE_PRECISION)
    created_at = Column(DateTime, server_default=func.current_timestamp())


Index("idx_interactions_user", UserInteraction.user_id)
Index("idx_interactions_target", UserInteraction.target_type, UserInteraction.target_id)
Index("idx_interactions_action", UserInteraction.action)
Index("idx_interactions_created", UserInteraction.created_at)
Index("idx_interactions_dwell", UserInteraction.dwell_seconds)