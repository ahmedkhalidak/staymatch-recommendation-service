"""
LocationHeatmap — tracks where users search by coordinates.
Clusters search locations to identify preferred neighborhoods/areas.
Uses lat/lng from search interactions to build a heatmap of interest areas.
"""
from collections import Counter
import math
from statistics import mean

from app.repositories.property_repo import InteractionRepository


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_CLUSTER_RADIUS = 1500


class LocationHeatmap:
    def __init__(self):
        self.interaction_repo = InteractionRepository()

    def analyze(self, user_id: str) -> dict:
        points = self.interaction_repo.get_location_clusters(user_id)
        if len(points) < 2:
            return {"status": "insufficient_data", "count": len(points)}

        coords = [(p.search_lat, p.search_lng) for p in points]
        clusters = self._cluster_coords(coords)

        top_areas = []
        for i, cluster in enumerate(clusters[:5]):
            lats = [c[0] for c in cluster]
            lngs = [c[1] for c in cluster]
            top_areas.append({
                "rank": i + 1,
                "center_lat": round(mean(lats), 6),
                "center_lng": round(mean(lngs), 6),
                "count": len(cluster),
                "radius_m": _CLUSTER_RADIUS,
            })

        return {
            "user_id": user_id,
            "total_points": len(coords),
            "clusters": len(clusters),
            "top_areas": top_areas,
        }

    def _cluster_coords(self, coords: list[tuple]) -> list[list]:
        if not coords:
            return []
        remaining = list(coords)
        clusters = []
        while remaining:
            seed = remaining.pop(0)
            cluster = [seed]
            still_remaining = []
            for c in remaining:
                if _haversine(seed[0], seed[1], c[0], c[1]) <= _CLUSTER_RADIUS:
                    cluster.append(c)
                else:
                    still_remaining.append(c)
            remaining = still_remaining
            clusters.append(cluster)
        clusters.sort(key=lambda c: len(c), reverse=True)
        return clusters