"""Unit tests for InteractionAnalyzer + UserClassifier + LocationHeatmap."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.interaction_analyzer import InteractionAnalyzer, UserClassifier
from app.services.location_heatmap import LocationHeatmap, _haversine

class TestInteractionAnalyzer:
    def test_not_enough_interactions(self):
        """Fewer than MIN_INTERACTIONS → skipped"""
        analyzer = InteractionAnalyzer()
        mock_repo = MagicMock()
        mock_repo.get_by_user.return_value = []
        analyzer.interaction_repo = mock_repo
        result = analyzer.analyze("user_x")
        assert result["status"] == "skipped"
        assert result["reason"] == "not enough interactions"

    def test_extract_preferences_basic(self):
        """Basic preference extraction"""
        analyzer = InteractionAnalyzer()
        props = [
            {"City": "Cairo", "Government": "Cairo", "PropertyType": 0,
             "MonthlyRent": 5000, "Furnished": True, "amenities": {}},
            {"City": "Cairo", "Government": "Cairo", "PropertyType": 0,
             "MonthlyRent": 6000, "Furnished": False, "amenities": {}},
        ]
        prefs = analyzer._extract_weighted_preferences(props, [], {})
        assert prefs["preferred_city"] == "Cairo"
        assert prefs["preferred_property_type"] == "full"

    def test_dwell_weight_high(self):
        """High dwell time (30s+) should add _dwell_high_count"""
        analyzer = InteractionAnalyzer()
        prefs = analyzer._extract_weighted_preferences(
            [{"Id": 1, "City": "Cairo", "Government": "Cairo", "PropertyType": 0,
              "MonthlyRent": 5000, "Furnished": True, "amenities": {}}],
            [],
            {1: 45}
        )
        assert prefs.get("_dwell_high_count", 0) == 1

class TestUserClassifier:
    def test_no_interactions(self):
        """No interactions → empty classification"""
        classifier = UserClassifier()
        classifier.interaction_repo = MagicMock()
        classifier.interaction_repo.get_by_user.return_value = []
        result = classifier.classify("user_x")
        assert result["segments"] == []

    def test_high_save_ratio(self):
        """High save ratio → decisive_buyer segment"""
        from tests.conftest import MockInteraction
        classifier = UserClassifier()
        mock_interactions = []
        for i in range(7):
            mock_interactions.append(MockInteraction(action="saved", dwell_seconds=5))
        for i in range(3):
            mock_interactions.append(MockInteraction(action="viewed", dwell_seconds=2))
        classifier.interaction_repo = MagicMock()
        classifier.interaction_repo.get_by_user.return_value = mock_interactions
        result = classifier.classify("user_x")
        assert "decisive_buyer" in result["segments"]

    def test_high_dwell(self):
        """High dwell time → careful_evaluator"""
        from tests.conftest import MockInteraction
        classifier = UserClassifier()
        mock_interactions = []
        for i in range(5):
            mock_interactions.append(MockInteraction(action="viewed", dwell_seconds=45))
        for i in range(5):
            mock_interactions.append(MockInteraction(action="viewed", dwell_seconds=2))
        classifier.interaction_repo = MagicMock()
        classifier.interaction_repo.get_by_user.return_value = mock_interactions
        result = classifier.classify("user_x")
        assert "careful_evaluator" in result["segments"]

    def test_premium_segment(self):
        """High max_budget → premium_segment"""
        classifier = UserClassifier()
        classifier.interaction_repo = MagicMock()
        classifier.interaction_repo.get_by_user.return_value = [
            type("obj", (object,), {"action": "viewed", "dwell_seconds": 5})()
        ]
        prefs = {"max_budget": 15000}
        result = classifier.classify("user_x", prefs)
        assert "premium_segment" in result["segments"]

class TestLocationHeatmap:
    def test_haversine_distance(self):
        """Known coordinates: Cairo to Giza ~30km"""
        dist = _haversine(30.0444, 31.2357, 30.0131, 31.2089)
        assert 3000 < dist < 6000

    def test_same_point(self):
        """Same point → 0 distance"""
        dist = _haversine(30.0444, 31.2357, 30.0444, 31.2357)
        assert dist == 0

    def test_insufficient_data(self):
        """Less than 2 points → insufficient_data"""
        hm = LocationHeatmap()
        mock_repo = MagicMock()
        mock_repo.get_location_clusters.return_value = [MagicMock(search_lat=30.0, search_lng=31.0)]
        hm.interaction_repo = mock_repo
        result = hm.analyze("user_x")
        assert result["status"] == "insufficient_data"

    def test_clustering(self):
        """Points within 1.5km should cluster together"""
        hm = LocationHeatmap()
        coords = [
            (30.0444, 31.2357),  # Cairo center
            (30.0500, 31.2400),  # ~500m away
            (31.2001, 29.9187),  # Alexandria (~200km away)
        ]
        clusters = hm._cluster_coords(coords)
        assert len(clusters) == 2  # Cairo cluster + Alexandria alone

    def test_all_far_apart(self):
        """Points > 1.5km apart → separate clusters"""
        hm = LocationHeatmap()
        coords = [(30.04, 31.24), (31.20, 29.92), (26.82, 33.48)]
        clusters = hm._cluster_coords(coords)
        assert len(clusters) == 3
