"""Unit tests for LocationScorer."""
import pytest
from app.services.scoring.location_scorer import LocationScorer
from tests.conftest import MockUser, MockProperty

scorer = LocationScorer()

class TestLocationScorer:
    def test_exact_city_match(self):
        """User prefers Cairo, property in Cairo → 1.0"""
        user = MockUser(preferred_city="Cairo", preferred_government=None)
        prop = MockProperty(city="Cairo", government="Cairo")
        assert scorer.score(user, prop) == 1.0

    def test_exact_government_match(self):
        """User prefers Giza gov, property in Giza → 1.0"""
        user = MockUser(preferred_city=None, preferred_government="Giza")
        prop = MockProperty(city="6 October", government="Giza")
        assert scorer.score(user, prop) == 1.0

    def test_no_location_preference(self):
        """No preference → neutral 0.5"""
        user = MockUser(preferred_city=None, preferred_government=None)
        prop = MockProperty(city="Cairo", government="Cairo")
        assert scorer.score(user, prop) == 0.5

    def test_different_governorates(self):
        """Different governorates, nearby → score < 1.0 but > 0"""
        user = MockUser(preferred_city="Cairo", preferred_government="Cairo")
        prop = MockProperty(city="Giza", government="Giza")
        score = scorer.score(user, prop)
        assert 0 < score < 1.0

    def test_context_location(self):
        """Location from context when user has none"""
        user = MockUser(gender="male", occupation="student")
        prop = MockProperty(city="Alexandria", government="Alexandria")
        context = {"preferred_city": "Alexandria"}
        assert scorer.score(user, prop, context) == 1.0
