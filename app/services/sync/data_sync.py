from datetime import datetime

from sqlalchemy import text

from app.database.session import get_session, get_mssql_engine


class DataSyncService:
    MAX_BATCH_SIZE = 500

    def __init__(self):
        self.pg_session = get_session()
        self.mssql_engine = get_mssql_engine()

    def sync_all(self, since: datetime = None):
        results = {}
        results["properties"] = self.sync_properties(since)
        results["rooms"] = self.sync_rooms(since)
        results["amenities"] = self.sync_amenities(since)
        results["allowed_tenants"] = self.sync_allowed_tenants(since)
        return results

    def sync_properties(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}
        query = "SELECT * FROM Properties WHERE IsDeleted = 0"
        if since:
            query += " AND LastModifiedAt > :since"
        with self.mssql_engine.connect() as mssql_conn:
            rows = mssql_conn.execute(text(query), {"since": since} if since else {})
            for row in rows:
                self._upsert_property(row)
        self.pg_session.commit()
        return {"status": "ok", "synced": "properties"}

    def sync_rooms(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}
        query = "SELECT * FROM Rooms WHERE IsDeleted = 0"
        if since:
            query += " AND LastModifiedAt > :since"
        with self.mssql_engine.connect() as mssql_conn:
            rows = mssql_conn.execute(text(query), {"since": since} if since else {})
            for row in rows:
                self._upsert_room(row)
        self.pg_session.commit()
        return {"status": "ok", "synced": "rooms"}

    def sync_amenities(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}
        query = "SELECT * FROM PropertyAmenities"
        if since:
            query += " WHERE LastModifiedAt > :since"
        with self.mssql_engine.connect() as mssql_conn:
            rows = mssql_conn.execute(text(query), {"since": since} if since else {})
            for row in rows:
                self._upsert_amenity(row)
        self.pg_session.commit()
        return {"status": "ok", "synced": "amenities"}

    def sync_allowed_tenants(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}
        query = "SELECT * FROM AllowedTenants WHERE IsDeleted = 0"
        if since:
            query += " AND LastModifiedAt > :since"
        with self.mssql_engine.connect() as mssql_conn:
            rows = mssql_conn.execute(text(query), {"since": since} if since else {})
            for row in rows:
                self._upsert_allowed_tenant(row)
        self.pg_session.commit()
        return {"status": "ok", "synced": "allowed_tenants"}

    def _upsert_property(self, row):
        stmt = text("""
            INSERT INTO synced_properties (
                id, owner_id, name, description, street, city, government,
                latitude, longitude, property_type, monthly_rent, deposit, size,
                number_of_bedrooms, number_of_living_rooms, total_rooms, available_rooms,
                furnished, minimum_stay, available_from, is_approved, created_at, last_modified
            ) VALUES (
                :id, :owner_id, :name, :description, :street, :city, :government,
                :latitude, :longitude, :property_type, :monthly_rent, :deposit, :size,
                :number_of_bedrooms, :number_of_living_rooms, :total_rooms, :available_rooms,
                :furnished, :minimum_stay, :available_from, :is_approved, :created_at, :last_modified
            )
            ON CONFLICT (id) DO UPDATE SET
                owner_id = EXCLUDED.owner_id, name = EXCLUDED.name,
                description = EXCLUDED.description, street = EXCLUDED.street,
                city = EXCLUDED.city, government = EXCLUDED.government,
                latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
                property_type = EXCLUDED.property_type, monthly_rent = EXCLUDED.monthly_rent,
                deposit = EXCLUDED.deposit, size = EXCLUDED.size,
                number_of_bedrooms = EXCLUDED.number_of_bedrooms,
                number_of_living_rooms = EXCLUDED.number_of_living_rooms,
                total_rooms = EXCLUDED.total_rooms, available_rooms = EXCLUDED.available_rooms,
                furnished = EXCLUDED.furnished, minimum_stay = EXCLUDED.minimum_stay,
                available_from = EXCLUDED.available_from, is_approved = EXCLUDED.is_approved,
                created_at = EXCLUDED.created_at, last_modified = EXCLUDED.last_modified,
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, self._PROPERTY_COLUMNS))

    def _upsert_room(self, row):
        stmt = text("""
            INSERT INTO synced_rooms (
                id, property_id, room_name, month_rent, deposit, capacity,
                capacity_available, furnished, ensuite_bathroom, shared_bathroom,
                balcony, window, pets_allowed, minimum_stay, available_from,
                is_deleted, created_at
            ) VALUES (
                :id, :property_id, :room_name, :month_rent, :deposit, :capacity,
                :capacity_available, :furnished, :ensuite_bathroom, :shared_bathroom,
                :balcony, :window, :pets_allowed, :minimum_stay, :available_from,
                :is_deleted, :created_at
            )
            ON CONFLICT (id) DO UPDATE SET
                property_id = EXCLUDED.property_id, room_name = EXCLUDED.room_name,
                month_rent = EXCLUDED.month_rent, deposit = EXCLUDED.deposit,
                capacity = EXCLUDED.capacity, capacity_available = EXCLUDED.capacity_available,
                furnished = EXCLUDED.furnished, ensuite_bathroom = EXCLUDED.ensuite_bathroom,
                shared_bathroom = EXCLUDED.shared_bathroom, balcony = EXCLUDED.balcony,
                window = EXCLUDED.window, pets_allowed = EXCLUDED.pets_allowed,
                minimum_stay = EXCLUDED.minimum_stay, available_from = EXCLUDED.available_from,
                is_deleted = EXCLUDED.is_deleted, created_at = EXCLUDED.created_at,
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, self._ROOM_COLUMNS))

    def _upsert_amenity(self, row):
        stmt = text("""
            INSERT INTO synced_amenities (
                property_id, wifi, tv, cooktop, oven, kettle, dishwasher,
                refrigerator, microwave, washer, free_parking, air_conditioning,
                smoke_alarm, fire_extinguisher
            ) VALUES (
                :property_id, :wifi, :tv, :cooktop, :oven, :kettle, :dishwasher,
                :refrigerator, :microwave, :washer, :free_parking, :air_conditioning,
                :smoke_alarm, :fire_extinguisher
            )
            ON CONFLICT (property_id) DO UPDATE SET
                wifi = EXCLUDED.wifi, tv = EXCLUDED.tv, cooktop = EXCLUDED.cooktop,
                oven = EXCLUDED.oven, kettle = EXCLUDED.kettle,
                dishwasher = EXCLUDED.dishwasher, refrigerator = EXCLUDED.refrigerator,
                microwave = EXCLUDED.microwave, washer = EXCLUDED.washer,
                free_parking = EXCLUDED.free_parking,
                air_conditioning = EXCLUDED.air_conditioning,
                smoke_alarm = EXCLUDED.smoke_alarm,
                fire_extinguisher = EXCLUDED.fire_extinguisher,
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, self._AMENITY_COLUMNS))

    def _upsert_allowed_tenant(self, row):
        stmt = text("""
            INSERT INTO synced_allowed_tenants (
                id, property_id, room_id, allows_families, allows_children,
                allows_students, student_gender, allows_workers, worker_gender, pets_allowed
            ) VALUES (
                :id, :property_id, :room_id, :allows_families, :allows_children,
                :allows_students, :student_gender, :allows_workers, :worker_gender, :pets_allowed
            )
            ON CONFLICT (id) DO UPDATE SET
                property_id = EXCLUDED.property_id, room_id = EXCLUDED.room_id,
                allows_families = EXCLUDED.allows_families,
                allows_children = EXCLUDED.allows_children,
                allows_students = EXCLUDED.allows_students,
                student_gender = EXCLUDED.student_gender,
                allows_workers = EXCLUDED.allows_workers,
                worker_gender = EXCLUDED.worker_gender,
                pets_allowed = EXCLUDED.pets_allowed,
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, self._ALLOWED_TENANT_COLUMNS))

    def _execute_upsert(self, stmt, params):
        self.pg_session.execute(stmt, params)

    @staticmethod
    def _map_row(row, columns):
        return {col: getattr(row, col, None) for col in columns}

    _PROPERTY_COLUMNS = [
        "id", "owner_id", "name", "description", "street", "city", "government",
        "latitude", "longitude", "property_type", "monthly_rent", "deposit", "size",
        "number_of_bedrooms", "number_of_living_rooms", "total_rooms", "available_rooms",
        "furnished", "minimum_stay", "available_from", "is_approved", "created_at", "last_modified"
    ]

    _ROOM_COLUMNS = [
        "id", "property_id", "room_name", "month_rent", "deposit", "capacity",
        "capacity_available", "furnished", "ensuite_bathroom", "shared_bathroom",
        "balcony", "window", "pets_allowed", "minimum_stay", "available_from",
        "is_deleted", "created_at"
    ]

    _AMENITY_COLUMNS = [
        "property_id", "wifi", "tv", "cooktop", "oven", "kettle", "dishwasher",
        "refrigerator", "microwave", "washer", "free_parking", "air_conditioning",
        "smoke_alarm", "fire_extinguisher"
    ]

    _ALLOWED_TENANT_COLUMNS = [
        "id", "property_id", "room_id", "allows_families", "allows_children",
        "allows_students", "student_gender", "allows_workers", "worker_gender", "pets_allowed"
    ]