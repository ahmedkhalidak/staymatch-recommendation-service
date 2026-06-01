"""Unit tests for utility modules: weights, location, geo distance."""
import pytest
from app.utils.weights import PROPERTY_WEIGHTS, ROOM_WEIGHTS
from app.utils.location import geo_distance, governorate_center

class TestWeights:
    def test_property_weights_sum(self):
        """Property weights sum to ~1.0"""
        total = sum(PROPERTY_WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_room_weights_sum(self):
        """Room weights sum to ~1.0"""
        total = sum(ROOM_WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_property_has_all_keys(self):
        """All required keys present"""
        required = {"budget", "location", "amenities", "tenant", "furnished", "property_type", "recency"}
        assert required.issubset(PROPERTY_WEIGHTS.keys())

    def test_room_has_all_keys(self):
        required = {"budget", "location", "capacity", "amenities", "tenant", "furnished", "room_type", "recency"}
        assert required.issubset(ROOM_WEIGHTS.keys())

class TestLocation:
    def test_geo_distance_cairo_alex(self):
        """Cairo to Alexandria ~180km"""
        dist = geo_distance(30.0444, 31.2357, 31.2001, 29.9187)
        assert 160 < dist < 200

    def test_geo_distance_zero(self):
        """Same point → 0"""
        dist = geo_distance(30.0444, 31.2357, 30.0444, 31.2357)
        assert dist == 0

    def test_geo_distance_none(self):
        """None coordinates → inf"""
        assert geo_distance(None, 31.2357, 30.0444, 31.2357) == float("inf")

    def test_governorate_center_cairo(self):
        """Cairo center exists"""
        center = governorate_center("cairo")
        assert center is not None
        assert center[0] == pytest.approx(30.0444, abs=0.01)

    def test_governorate_center_unknown(self):
        """Unknown governorate → None"""
        assert governorate_center("nonexistent") is None

    def test_governorate_center_case_insensitive(self):
        """Case insensitive lookup"""
        center = governorate_center("CAIRO")
        assert center is not None
