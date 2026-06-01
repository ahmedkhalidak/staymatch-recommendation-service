from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database.models.base import Base


class SyncedProperty(Base):
    __tablename__ = "synced_properties"

    id = Column(Integer, primary_key=True)
    owner_id = Column(String(255))
    name = Column(Text)
    description = Column(Text)
    street = Column(Text)
    city = Column(Text)
    government = Column(Text)
    latitude = Column(DOUBLE_PRECISION)
    longitude = Column(DOUBLE_PRECISION)
    property_type = Column(Integer, nullable=False)
    monthly_rent = Column(DOUBLE_PRECISION)
    deposit = Column(DOUBLE_PRECISION)
    size = Column(DOUBLE_PRECISION)
    number_of_bedrooms = Column(Integer)
    number_of_living_rooms = Column(Integer)
    total_rooms = Column(Integer)
    available_rooms = Column(Integer)
    furnished = Column(Boolean)
    minimum_stay = Column(Integer)
    available_from = Column(DateTime)
    is_approved = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    last_modified = Column(DateTime)
    synced_at = Column(DateTime, server_default=func.current_timestamp())

    rooms = relationship("SyncedRoom", back_populates="property")
    amenities = relationship("SyncedAmenity", uselist=False, back_populates="property")
    allowed_tenants = relationship("SyncedAllowedTenant", back_populates="property")


Index("idx_synced_properties_city", SyncedProperty.city)
Index("idx_synced_properties_government", SyncedProperty.government)
Index("idx_synced_properties_property_type", SyncedProperty.property_type)
Index("idx_synced_properties_monthly_rent", SyncedProperty.monthly_rent)
Index("idx_synced_properties_is_approved", SyncedProperty.is_approved)
Index("idx_synced_properties_location", SyncedProperty.latitude, SyncedProperty.longitude)
Index("idx_synced_properties_synced_at", SyncedProperty.synced_at)


class SyncedRoom(Base):
    __tablename__ = "synced_rooms"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("synced_properties.id"), nullable=False)
    room_name = Column(Text)
    month_rent = Column(DOUBLE_PRECISION)
    deposit = Column(DOUBLE_PRECISION)
    capacity = Column(Integer)
    capacity_available = Column(Integer)
    furnished = Column(Boolean)
    ensuite_bathroom = Column(Boolean)
    shared_bathroom = Column(Boolean)
    balcony = Column(Boolean)
    window = Column(Boolean)
    pets_allowed = Column(Boolean)
    minimum_stay = Column(Integer)
    available_from = Column(DateTime)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime)
    synced_at = Column(DateTime, server_default=func.current_timestamp())

    property = relationship("SyncedProperty", back_populates="rooms")
    allowed_tenants = relationship("SyncedAllowedTenant", back_populates="room")


Index("idx_synced_rooms_property", SyncedRoom.property_id)
Index("idx_synced_rooms_month_rent", SyncedRoom.month_rent)
Index("idx_synced_rooms_capacity_avail", SyncedRoom.capacity_available)
Index("idx_synced_rooms_synced_at", SyncedRoom.synced_at)


class SyncedAmenity(Base):
    __tablename__ = "synced_amenities"

    property_id = Column(Integer, ForeignKey("synced_properties.id"), primary_key=True)
    wifi = Column(Boolean)
    tv = Column(Boolean)
    cooktop = Column(Boolean)
    oven = Column(Boolean)
    kettle = Column(Boolean)
    dishwasher = Column(Boolean)
    refrigerator = Column(Boolean)
    microwave = Column(Boolean)
    washer = Column(Boolean)
    free_parking = Column(Boolean)
    air_conditioning = Column(Boolean)
    smoke_alarm = Column(Boolean)
    fire_extinguisher = Column(Boolean)
    synced_at = Column(DateTime, server_default=func.current_timestamp())

    property = relationship("SyncedProperty", back_populates="amenities")


class SyncedAllowedTenant(Base):
    __tablename__ = "synced_allowed_tenants"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("synced_properties.id"))
    room_id = Column(Integer, ForeignKey("synced_rooms.id"))
    allows_families = Column(Boolean)
    allows_children = Column(Boolean)
    allows_students = Column(Boolean)
    student_gender = Column(Integer)
    allows_workers = Column(Boolean)
    worker_gender = Column(Integer)
    pets_allowed = Column(Boolean)
    synced_at = Column(DateTime, server_default=func.current_timestamp())

    property = relationship("SyncedProperty", back_populates="allowed_tenants")
    room = relationship("SyncedRoom", back_populates="allowed_tenants")


Index("idx_synced_allowed_tenants_property", SyncedAllowedTenant.property_id)
Index("idx_synced_allowed_tenants_room", SyncedAllowedTenant.room_id)