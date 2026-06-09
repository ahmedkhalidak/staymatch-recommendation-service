"""Unit tests for Ranker + PropertyRecommender + RoomRecommender."""
import pytest
from app.services.ranking.ranker import Ranker
from app.services.recommendation.property_recommender import PropertyRecommender, RoomRecommender
from app.utils.weights import PROPERTY_WEIGHTS, ROOM_WEIGHTS
from tests.conftest import MockUser, MockProperty, MockRoom, MockAllowedTenant, MockAmenity

class TestRanker:
    def test_weighted_sum_perfect(self):
        """All scores 1.0 → result is 1.0"""
        ranker = Ranker(PROPERTY_WEIGHTS)
        breakdown = {k: 1.0 for k in PROPERTY_WEIGHTS}
        assert ranker.weighted_sum(breakdown) == pytest.approx(1.0)

    def test_weighted_sum_zero(self):
        """All scores 0.0 → result is 0.0"""
        ranker = Ranker(PROPERTY_WEIGHTS)
        breakdown = {k: 0.0 for k in PROPERTY_WEIGHTS}
        assert ranker.weighted_sum(breakdown) == 0.0

    def test_weighted_sum_mixed(self):
        """Mixed scores should produce intermediate result"""
        ranker = Ranker({"budget": 0.30, "location": 0.25})
        breakdown = {"budget": 1.0, "location": 0.0}
        expected = (0.30 * 1.0 + 0.25 * 0.0) / 0.55
        assert ranker.weighted_sum(breakdown) == pytest.approx(expected)

    def test_empty_breakdown(self):
        """Empty breakdown → 0.0"""
        ranker = Ranker(PROPERTY_WEIGHTS)
        assert ranker.weighted_sum({}) == 0.0

class TestPropertyRecommender:
    def test_property_ranking_order(self, sample_properties, male_user):
        """Higher score properties come first"""
        rec = PropertyRecommender()
        ctx = {"max_budget": 6000, "min_budget": 3000,
               "preferred_city": "Cairo", "preferred_government": "Cairo"}
        scored = rec.recommend(male_user, sample_properties, ctx)
        assert len(scored) == 3
        scores = [s for _, s, _ in scored]
        assert scores == sorted(scores, reverse=True)

    def test_property_breakdown_jsonb(self, sample_properties, male_user):
        """Score breakdown should have correct keys"""
        rec = PropertyRecommender()
        ctx = {"max_budget": 6000, "min_budget": 3000,
               "preferred_city": "Cairo", "preferred_government": "Cairo"}
        scored = rec.recommend(male_user, sample_properties, ctx)
        _, _, breakdown = scored[0]
        for key in ["budget", "location", "amenities", "tenant", "furnished", "property_type", "recency"]:
            assert key in breakdown

class TestRoomRecommender:
    def test_room_diversity_rule(self, sample_rooms):
        """No more than 2 results from same property"""
        rec = RoomRecommender()
        user = MockUser(gender="male", occupation="student", min_budget=1000, max_budget=5000)
        # Add extra room from property_id=1 to test diversity
        extra_room = MockRoom(id=4, property_id=1, month_rent=1800, capacity=3,
                               capacity_available=1, furnished=False, shared_bathroom=True)
        rooms = sample_rooms + [extra_room]
        scored = rec.recommend(user, rooms, {})
        # Count results per property
        from collections import Counter
        prop_counts = Counter(r[3].id if r[3] else None for r in scored)
        for pid, count in prop_counts.items():
            if pid is not None:
                assert count <= 2

    def test_room_capacity_scoring(self):
        """Rooms with available capacity score higher"""
        rec = RoomRecommender()
        room_full = MockRoom(id=1, property_id=1, month_rent=2000, capacity=2, capacity_available=0)
        room_avail = MockRoom(id=2, property_id=1, month_rent=2000, capacity=2, capacity_available=2)
        assert rec._capacity_score(room_avail) > rec._capacity_score(room_full)

    def test_room_ensuite_premium(self):
        """Ensuite bathroom rooms score higher than shared"""
        rec = RoomRecommender()
        room_ensuite = MockRoom(id=1, property_id=1, ensuite_bathroom=True, shared_bathroom=False)
        room_shared = MockRoom(id=2, property_id=1, ensuite_bathroom=False, shared_bathroom=True)
        assert rec._room_type_score(room_ensuite) > rec._room_type_score(room_shared)
