from datetime import datetime
from math import ceil
import logging

from sqlalchemy import text

from app.database.session import get_session, get_mssql_engine
from app.database.models.property import SyncedProperty, SyncedRoom, SyncedAmenity, SyncedAllowedTenant
from app.database.models.user import UserProfile

logger = logging.getLogger("staymatch.sync")


class DataSyncService:
    MAX_BATCH_SIZE = 500

    MSSQL_USER_TABLES = ["AspNetUsers", "Users"]

    def __init__(self):
        self.pg_session = get_session()
        self.mssql_engine = get_mssql_engine()

        self._PROPERTY_COLUMNS = [c.name for c in SyncedProperty.__table__.columns]
        self._ROOM_COLUMNS = [c.name for c in SyncedRoom.__table__.columns]
        self._AMENITY_COLUMNS = [c.name for c in SyncedAmenity.__table__.columns]
        self._ALLOWED_TENANT_COLUMNS = [c.name for c in SyncedAllowedTenant.__table__.columns]

    def sync_all(self, since: datetime = None):
        results = {}
        results["properties"] = self.sync_properties(since)
        results["rooms"] = self.sync_rooms(since)
        results["amenities"] = self.sync_amenities(since)
        results["allowed_tenants"] = self.sync_allowed_tenants(since)
        results["users"] = self.sync_users(since)
        results["user_preferences"] = self.sync_user_preferences(since)
        return results

    def _sync_table(self, table_name, columns, upsert_method, base_query, since_field=None, since=None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}

        query = base_query
        params = {}
        if since and since_field:
            query += f" AND {since_field} > :since"
            params["since"] = since

        with self.mssql_engine.connect() as mssql_conn:
            result = mssql_conn.execute(text(query), params if params else {})
            rows = result.fetchall()
            total = len(rows)
            batches = ceil(total / self.MAX_BATCH_SIZE) if total > 0 else 1

            for batch_num in range(batches):
                start = batch_num * self.MAX_BATCH_SIZE
                end = start + self.MAX_BATCH_SIZE
                batch = rows[start:end]
                for row in batch:
                    upsert_method(row)
                self.pg_session.commit()

        return {"status": "ok", "synced": table_name, "count": total}

    def sync_properties(self, since: datetime = None):
        return self._sync_table(
            "properties", self._PROPERTY_COLUMNS, self._upsert_property,
            "SELECT * FROM Properties WHERE IsDeleted = 0",
            since_field="LastModifiedAt", since=since
        )

    def sync_rooms(self, since: datetime = None):
        return self._sync_table(
            "rooms", self._ROOM_COLUMNS, self._upsert_room,
            "SELECT * FROM Rooms WHERE IsDeleted = 0",
            since_field="LastModifiedAt", since=since
        )

    def sync_amenities(self, since: datetime = None):
        return self._sync_table(
            "amenities", self._AMENITY_COLUMNS, self._upsert_amenity,
            "SELECT * FROM PropertyAmenities",
            since_field="LastModifiedAt", since=since
        )

    def sync_allowed_tenants(self, since: datetime = None):
        return self._sync_table(
            "allowed_tenants", self._ALLOWED_TENANT_COLUMNS, self._upsert_allowed_tenant,
            "SELECT * FROM AllowedTenants WHERE IsDeleted = 0",
            since_field="LastModifiedAt", since=since
        )

    def sync_users(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}

        user_table = self._detect_user_table()
        if not user_table:
            logger.warning("No AspNetUsers or Users table found in MSSQL — user sync skipped")
            return {"status": "skipped", "reason": "no_user_table"}

        try:
            col_query = text(
                f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = :t"
            )
            with self.mssql_engine.connect() as conn:
                existing_cols = {row[0] for row in conn.execute(col_query, {"t": user_table}).fetchall()}
        except Exception:
            existing_cols = set()

        safe_cols = {"Id", "UserName", "Email", "PhoneNumber", "Gender", "BirthYear",
                     "Nationality", "Occupation", "CreatedAt", "LastModifiedAt"}
        available = [c for c in safe_cols if c in existing_cols]

        if not available:
            available = ["Id", "UserName"]

        query = f"SELECT {', '.join(available)} FROM {user_table}"
        if since and "LastModifiedAt" in available:
            query += " WHERE LastModifiedAt > :since"

        synced = 0
        try:
            with self.mssql_engine.connect() as mssql_conn:
                params = {}
                if since and "LastModifiedAt" in available:
                    params["since"] = since
                result = mssql_conn.execute(text(query), params if params else {})
                rows = result.fetchall()
                for row in rows:
                    self._upsert_user(row, available)
                    synced += 1
                self.pg_session.commit()
        except Exception as e:
            logger.error("User sync failed: %s", e)
            return {"status": "error", "reason": str(e)}

        return {"status": "ok", "synced": "users", "count": synced, "table": user_table}

    def sync_user_preferences(self, since: datetime = None):
        if not self.mssql_engine:
            return {"status": "no_mssql_engine"}

        try:
            with self.mssql_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_NAME IN ('UserPreferences', 'UserProfiles', 'SearchPreferences')"
                ))
                pref_tables = [row[0] for row in result.fetchall()]
        except Exception:
            pref_tables = []

        if not pref_tables:
            return {"status": "skipped", "reason": "no_preferences_table"}

        pref_table = pref_tables[0]
        result = {"status": "ok", "synced": pref_table}

        try:
            col_query = text(
                f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = :t"
            )
            with self.mssql_engine.connect() as conn:
                cols = {row[0] for row in conn.execute(col_query, {"t": pref_table}).fetchall()}
        except Exception:
            return {"status": "skipped", "reason": "cannot_read_columns"}

        required = {"UserId", "MinBudget", "MaxBudget", "PreferredCity"}
        if not required.issubset(cols):
            logger.info("UserPreferences table lacks required columns — skipping")
            return {"status": "skipped", "reason": "missing_columns"}

        query = f"SELECT * FROM {pref_table}"
        synced = 0
        try:
            with self.mssql_engine.connect() as mssql_conn:
                rows = mssql_conn.execute(text(query)).fetchall()
                for row in rows:
                    self._upsert_user_preference(row, cols)
                    synced += 1
                self.pg_session.commit()
        except Exception as e:
            logger.error("User preferences sync failed: %s", e)
            return {"status": "error", "reason": str(e)}

        result["count"] = synced
        return result

    def _detect_user_table(self):
        try:
            with self.mssql_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_NAME IN ('AspNetUsers', 'Users')"
                ))
                tables = [row[0] for row in result.fetchall()]
                return tables[0] if tables else None
        except Exception:
            return None

    def _upsert_property(self, row):
        stmt = text(f"""
            INSERT INTO synced_properties ({", ".join(self._PROPERTY_COLUMNS)})
            VALUES ({", ".join(f":{c}" for c in self._PROPERTY_COLUMNS)})
            ON CONFLICT (id) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in self._PROPERTY_COLUMNS if c != "id")},
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, self._PROPERTY_COLUMNS))

    def _upsert_room(self, row):
        columns = [c for c in self._ROOM_COLUMNS if c not in ("synced_at",)]
        stmt = text(f"""
            INSERT INTO synced_rooms ({", ".join(columns)})
            VALUES ({", ".join(f":{c}" for c in columns)})
            ON CONFLICT (id) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id")},
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, columns))

    def _upsert_amenity(self, row):
        columns = [c for c in self._AMENITY_COLUMNS if c not in ("synced_at",)]
        stmt = text(f"""
            INSERT INTO synced_amenities ({", ".join(columns)})
            VALUES ({", ".join(f":{c}" for c in columns)})
            ON CONFLICT (property_id) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "property_id")},
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, columns))

    def _upsert_allowed_tenant(self, row):
        columns = [c for c in self._ALLOWED_TENANT_COLUMNS if c not in ("synced_at",)]
        stmt = text(f"""
            INSERT INTO synced_allowed_tenants ({", ".join(columns)})
            VALUES ({", ".join(f":{c}" for c in columns)})
            ON CONFLICT (id) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id")},
                synced_at = CURRENT_TIMESTAMP
        """)
        self._execute_upsert(stmt, self._map_row(row, columns))

    def _upsert_user(self, row, columns):
        data = {}
        user_id = getattr(row, "Id", None) or getattr(row, "id", None)
        if not user_id:
            return
        data["external_user_id"] = str(user_id)

        if "UserName" in columns:
            data["full_name"] = getattr(row, "UserName", None)
        if "Email" in columns:
            data["email"] = getattr(row, "Email", None) if hasattr(row, "Email") else None
        if "PhoneNumber" in columns:
            data["phone"] = getattr(row, "PhoneNumber", None)
        if "Gender" in columns:
            data["gender"] = getattr(row, "Gender", None)
        if "BirthYear" in columns:
            data["birth_year"] = getattr(row, "BirthYear", None)
        if "Nationality" in columns:
            data["nationality"] = getattr(row, "Nationality", None)
        if "Occupation" in columns:
            data["occupation"] = getattr(row, "Occupation", None)

        existing = self.pg_session.query(UserProfile).filter(
            UserProfile.external_user_id == data["external_user_id"]
        ).first()
        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
        else:
            self.pg_session.add(UserProfile(**data))

    def _upsert_user_preference(self, row, columns):
        from app.database.models.user import UserSearchPreference
        from sqlalchemy import text as sa_text

        data = {"user_id": str(getattr(row, "UserId", ""))}
        if not data["user_id"]:
            return

        if "MinBudget" in columns:
            data["min_budget"] = getattr(row, "MinBudget", None)
        if "MaxBudget" in columns:
            data["max_budget"] = getattr(row, "MaxBudget", None)
        if "PreferredCity" in columns:
            data["preferred_city"] = getattr(row, "PreferredCity", None)
        if "PreferredGovernment" in columns:
            data["preferred_government"] = getattr(row, "PreferredGovernment", None)
        if "Furnished" in columns:
            data["furnished"] = getattr(row, "Furnished", None)
        if "Wifi" in columns:
            data["wifi"] = getattr(row, "Wifi", None)
        if "AirConditioning" in columns:
            data["air_conditioning"] = getattr(row, "AirConditioning", None)

        stmt = sa_text("""
            INSERT INTO user_search_preferences
                (user_id, min_budget, max_budget, preferred_city, preferred_government,
                 furnished, wifi, air_conditioning)
            VALUES
                (:user_id, :min_budget, :max_budget, :preferred_city, :preferred_government,
                 :furnished, :wifi, :air_conditioning)
            ON CONFLICT (user_id) DO UPDATE SET
                min_budget = EXCLUDED.min_budget,
                max_budget = EXCLUDED.max_budget,
                preferred_city = EXCLUDED.preferred_city,
                preferred_government = EXCLUDED.preferred_government,
                furnished = EXCLUDED.furnished,
                wifi = EXCLUDED.wifi,
                air_conditioning = EXCLUDED.air_conditioning
        """)
        self.pg_session.execute(stmt, data)

    def _execute_upsert(self, stmt, params):
        self.pg_session.execute(stmt, params)

    @staticmethod
    def _map_row(row, columns):
        return {col: getattr(row, col, None) for col in columns}