from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, UniqueConstraint, Text
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


class PropertyRecommendation(Base):
    __tablename__ = "property_recommendations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    property_id = Column(Integer, ForeignKey("synced_properties.id"), nullable=False)
    score = Column(Float, nullable=False)
    score_breakdown = Column(JSONB)
    rank = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("user_id", "property_id"),
    )


Index("idx_prop_rec_user", PropertyRecommendation.user_id)
Index("idx_prop_rec_score", PropertyRecommendation.score.desc())
Index("idx_prop_rec_expires", PropertyRecommendation.expires_at)


class RoomRecommendation(Base):
    __tablename__ = "room_recommendations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    room_id = Column(Integer, ForeignKey("synced_rooms.id"), nullable=False)
    score = Column(Float, nullable=False)
    score_breakdown = Column(JSONB)
    rank = Column(Integer)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("user_id", "room_id"),
    )


Index("idx_room_rec_user", RoomRecommendation.user_id)
Index("idx_room_rec_score", RoomRecommendation.score.desc())


class RoommateMatch(Base):
    __tablename__ = "roommate_matches"

    id = Column(Integer, primary_key=True)
    seeker_user_id = Column(String(255), nullable=False)
    room_id = Column(Integer, ForeignKey("synced_rooms.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("synced_properties.id"), nullable=False)
    room_compatibility_score = Column(Float, nullable=False)
    match_breakdown = Column(JSONB)
    current_roommates = Column(JSONB)
    seeker_questionnaire_match = Column(Float)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("seeker_user_id", "room_id"),
    )


Index("idx_match_seeker", RoommateMatch.seeker_user_id)
Index("idx_match_room", RoommateMatch.room_id)
Index("idx_match_score", RoommateMatch.room_compatibility_score.desc())
Index("idx_match_expires", RoommateMatch.expires_at)


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