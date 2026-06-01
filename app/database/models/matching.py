from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database.models.base import Base


class PropertyEmbedding(Base):
    __tablename__ = "property_embeddings"

    property_id = Column(Integer, ForeignKey("synced_properties.id"), primary_key=True)
    embedding = Column(JSONB)
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"

    user_id = Column(String(255), primary_key=True)
    embedding = Column(JSONB)
    updated_at = Column(DateTime, server_default=func.current_timestamp())