"""Unit tests for AmenityScorer."""
import pytest
from app.services.scoring.amenity_scorer import AmenityScorer
from conftest import MockUser, MockProperty, MockAmenity

scorer = AmenityScorer()

class TestAmenityScorer:
    def test_all_amenities_match(self):
        """User wants wifi+AC, property has wifi+AC → 1.0"""
        user = MockUser(wifi=True, air_conditioning=True)
        prop = MockProperty()
        amenities = MockAmenity(wifi=True, air_conditioning=True, balcony=False)
        context = {"amenities": amenities, "preferences": user}
        assert scorer.score(user, prop, context) == 1.0

    def test_partial_match(self):
        """User wants wifi+AC+balcony, property has wifi only → 0.33"""
        user = MockUser(wifi=True, air_conditioning=True, balcony=True)
        prop = MockProperty()
        amenities = MockAmenity(wifi=True, air_conditioning=False, balcony=False)
        context = {"amenities": amenities, "preferences": user}
        assert scorer.score(user, prop, context) == pytest.approx(1/3)

    def test_no_amenities_wanted(self):
        """User has no amenity preferences → neutral 0.5"""
        user = MockUser(wifi=False, air_conditioning=False)
        prop = MockProperty()
        context = {"amenities": MockAmenity(wifi=True)}
        assert scorer.score(user, prop, context) == 0.5

    def test_no_amenities_on_property(self):
        """No amenities data on property → neutral 0.5"""
        user = MockUser(wifi=True, air_conditioning=True)
        prop = MockProperty()
        context = {"amenities": None}
        assert scorer.score(user, prop, context) == 0.5

    def test_furnished_as_amenity(self):
        """User wants furnished, property has it → counts as match"""
        user = MockUser(furnished=True, wifi=False)
        prop = MockProperty(furnished=True)
        amenities = MockAmenity(wifi=False)
        context = {"amenities": amenities, "preferences": user}
        assert scorer.score(user, prop, context) == 1.0
