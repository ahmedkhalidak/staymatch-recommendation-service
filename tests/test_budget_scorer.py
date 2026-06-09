"""Unit tests for BudgetScorer — covers all rent scenarios."""
import pytest
from app.services.scoring.budget_scorer import BudgetScorer
from tests.conftest import MockUser, MockProperty

scorer = BudgetScorer()

class TestBudgetScorer:
    def test_perfect_fit(self):
        """Rent within budget range → 1.0"""
        user = MockUser(min_budget=4000, max_budget=6000)
        prop = MockProperty(monthly_rent=5000)
        assert scorer.score(user, prop) == 1.0

    def test_below_min_budget(self):
        """Rent below minimum → proportional score (< 1.0)"""
        user = MockUser(min_budget=5000, max_budget=10000)
        prop = MockProperty(monthly_rent=3000)
        score = scorer.score(user, prop)
        assert 0.0 < score < 1.0
        assert score == pytest.approx(3000/5000)

    def test_slightly_over_budget(self):
        """Up to 20% over max → 0.7"""
        user = MockUser(min_budget=3000, max_budget=5000)
        prop = MockProperty(monthly_rent=5800)
        assert scorer.score(user, prop) == 0.7

    def test_way_over_budget(self):
        """Over 20% beyond max → degrades linearly"""
        user = MockUser(min_budget=2000, max_budget=3000)
        prop = MockProperty(monthly_rent=6000)
        score = scorer.score(user, prop)
        assert 0.0 <= score < 0.7

    def test_no_min_budget(self):
        """Only max set, rent under max → 0.9"""
        user = MockUser(min_budget=None, max_budget=5000)
        prop = MockProperty(monthly_rent=4000)
        assert scorer.score(user, prop) == 0.9

    def test_no_max_budget(self):
        """No budget set → neutral 0.5"""
        user = MockUser(min_budget=None, max_budget=None)
        prop = MockProperty(monthly_rent=5000)
        assert scorer.score(user, prop) == 0.5

    def test_no_rent(self):
        """No monthly_rent → neutral 0.5"""
        user = MockUser(min_budget=3000, max_budget=6000)
        prop = MockProperty(monthly_rent=None)
        assert scorer.score(user, prop) == 0.5

    def test_exactly_at_min_budget(self):
        """Rent exactly at minimum → 1.0"""
        user = MockUser(min_budget=5000, max_budget=10000)
        prop = MockProperty(monthly_rent=5000)
        assert scorer.score(user, prop) == 1.0

    def test_context_budget(self):
        """Budget from context when user has none"""
        user = MockUser(gender="male", occupation="student")
        prop = MockProperty(monthly_rent=3000)
        context = {"max_budget": 5000, "min_budget": 2000}
        assert scorer.score(user, prop, context) == 1.0

    def test_below_min_zero(self):
        """Rent far below min → approaches 0"""
        user = MockUser(min_budget=10000, max_budget=20000)
        prop = MockProperty(monthly_rent=100)
        score = scorer.score(user, prop)
        assert score == pytest.approx(100/10000)
