"""Direct MSSQL property reader — no sync needed."""
import logging
from sqlalchemy import text

from app.database.session import get_mssql_engine

logger = logging.getLogger("staymatch.mssql")


def get_property_by_id(property_id: int):
    engine = get_mssql_engine()
    if not engine:
        logger.error("get_property_by_id(%s): no MSSQL engine available", property_id)
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT p.Id, p.Name, p.City, p.Government, p.Latitude, p.Longitude,
                           p.PropertyType, p.MonthlyRent, p.Deposite, p.Size,
                           p.Furnished, p.NumberOfBedrooms, p.TotalRooms, p.AvailableRooms,
                           p.CreatedAt, p.Street
                    FROM Properties p
                    WHERE p.Id = :id AND p.IsDeleted = 0 AND p.IsApproved = 1
                """),
                {"id": property_id}
            ).mappings().first()
            if not row:
                return None
            amenities = conn.execute(
                text("SELECT * FROM PropertyAmenities WHERE PropertyId = :id"),
                {"id": property_id}
            ).mappings().first()
            result = dict(row)
            result["amenities"] = dict(amenities) if amenities else {}
            return result
    except Exception as e:
        logger.error("get_property_by_id(%s) failed: %s", property_id, e)
        return None


def get_properties_batch(property_ids: list[int]):
    if not property_ids:
        return []
    engine = get_mssql_engine()
    if not engine:
        logger.error("get_properties_batch(%s ids): no MSSQL engine", len(property_ids))
        return []
    try:
        ids = list(set(property_ids))
        placeholders = ",".join(f":id_{i}" for i in range(len(ids)))
        params = {f"id_{i}": v for i, v in enumerate(ids)}
        with engine.connect() as conn:
            rows = conn.execute(
                text(f"""
                    SELECT p.Id, p.Name, p.City, p.Government, p.Latitude, p.Longitude,
                           p.PropertyType, p.MonthlyRent, p.Deposite, p.Size,
                           p.Furnished, p.NumberOfBedrooms, p.TotalRooms, p.AvailableRooms,
                           p.CreatedAt, p.Street
                    FROM Properties p
                    WHERE p.Id IN ({placeholders}) AND p.IsDeleted = 0 AND p.IsApproved = 1
                """),
                params
            ).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error("get_properties_batch(%d ids) failed: %s", len(property_ids), e)
        return []


def get_room_by_id(room_id: int):
    engine = get_mssql_engine()
    if not engine:
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT r.Id, r.RoomName, r.Month_rent, r.Deposit, r.Capacity,
                           r.CapacityAvailable, r.Furnished, r.EnSuiteBathroom,
                           r.SharedBathroom, r.Balcony, r.Window, r.PetsAllowed,
                           r.PropertyId, p.City, p.Government, p.Name as PropertyName
                    FROM Rooms r
                    JOIN Properties p ON r.PropertyId = p.Id
                    WHERE r.Id = :id AND r.IsDeleted = 0 AND p.IsDeleted = 0
                """),
                {"id": room_id}
            ).mappings().first()
            return dict(row) if row else None
    except Exception as e:
        logger.error("get_room_by_id(%s) failed: %s", room_id, e)
        return None
