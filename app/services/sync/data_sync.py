from datetime import datetime
from math import ceil

from sqlalchemy import text

from app.database.session import get_session, get_mssql_engine
from app.database.models.property import SyncedProperty, SyncedRoom, SyncedAmenity, SyncedAllowedTenant


class DataSyncService:
    MAX_BATCH_SIZE = 500

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

    def _execute_upsert(self, stmt, params):
        self.pg_session.execute(stmt, params)

    @staticmethod
    def _map_row(row, columns):
        return {col: getattr(row, col, None) for col in columns}