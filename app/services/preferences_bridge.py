"""
Preferences Bridge — syncs user preferences between chatbot service and recommendation service.
Both services share the same Neon PostgreSQL. The chatbot stores preferences in `user_preferences`
while the recommendation service uses `user_search_preferences`. This bridge keeps them in sync.
"""
import logging
from app.database.session import get_session
from sqlalchemy import text

logger = logging.getLogger("staymatch.bridge")


class PreferencesBridge:
    def __init__(self):
        self.session = get_session()

    def sync_all(self):
        """Sync all user_preferences from chatbot table into user_search_preferences."""
        try:
            rows = self.session.execute(
                text("SELECT * FROM user_preferences")
            ).mappings().all()
        except Exception as e:
            logger.warning("Cannot read chatbot user_preferences: %s", e)
            return {"synced": 0}

        synced = 0
        for row in rows:
            data = {"user_id": row["user_id"]}
            if row.get("min_budget"):
                data["min_budget"] = row["min_budget"]
            if row.get("max_budget"):
                data["max_budget"] = row["max_budget"]
            if row.get("preferred_location"):
                data["preferred_city"] = row["preferred_location"]
                data["preferred_government"] = row["preferred_location"]
            if row.get("tenant_type"):
                data["tenant_type"] = row["tenant_type"]
            if row.get("gender"):
                data["gender_preference"] = row["gender"]
            if row.get("furnished"):
                data["furnished"] = row["furnished"]
            if row.get("wifi"):
                data["wifi"] = row["wifi"]
            if row.get("air_conditioning"):
                data["air_conditioning"] = row["air_conditioning"]
            if row.get("balcony"):
                data["balcony"] = row["balcony"]
            if row.get("private_bathroom"):
                data["private_bathroom"] = row["private_bathroom"]
            if row.get("shared_room"):
                data["shared_room"] = row["shared_room"]

            self.session.execute(
                text("""
                    INSERT INTO user_search_preferences 
                        (user_id, min_budget, max_budget, preferred_city, preferred_government,
                         tenant_type, gender_preference, furnished, wifi, air_conditioning,
                         balcony, private_bathroom, shared_room)
                    VALUES 
                        (:user_id, :min_budget, :max_budget, :preferred_city, :preferred_government,
                         :tenant_type, :gender_preference, :furnished, :wifi, :air_conditioning,
                         :balcony, :private_bathroom, :shared_room)
                    ON CONFLICT (user_id) DO UPDATE SET
                        min_budget = EXCLUDED.min_budget,
                        max_budget = EXCLUDED.max_budget,
                        preferred_city = EXCLUDED.preferred_city,
                        preferred_government = EXCLUDED.preferred_government,
                        tenant_type = EXCLUDED.tenant_type,
                        gender_preference = EXCLUDED.gender_preference,
                        furnished = EXCLUDED.furnished,
                        wifi = EXCLUDED.wifi,
                        air_conditioning = EXCLUDED.air_conditioning,
                        balcony = EXCLUDED.balcony,
                        private_bathroom = EXCLUDED.private_bathroom,
                        shared_room = EXCLUDED.shared_room
                """),
                data
            )
            synced += 1

        self.session.commit()
        logger.info("PreferencesBridge synced %d users from chatbot preferences", synced)
        return {"synced": synced}
