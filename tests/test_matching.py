"""Unit tests for CompatibilityEngine."""
import pytest
from app.services.matching.compatibility_engine import CompatibilityEngine

class TestQuestionnaireSimilarity:
    def setup_method(self):
        self.engine = CompatibilityEngine()

    def test_same_answers(self):
        score = self.engine._questionnaire_similarity({"1": "male", "2": "student"}, {"1": "male", "2": "student"})
        assert score == 1.0

    def test_completely_different(self):
        score = self.engine._questionnaire_similarity({"1": "yes"}, {"1": "no"})
        assert score == 0.0

    def test_no_shared_questions(self):
        score = self.engine._questionnaire_similarity({"1": "yes"}, {"2": "no"})
        assert score == 0.5

    def test_scale_close(self):
        score = self.engine._questionnaire_similarity({"10": 4}, {"10": 5})
        assert score == pytest.approx(0.75)

    def test_scale_same(self):
        score = self.engine._questionnaire_similarity({"10": 3}, {"10": 3})
        assert score == 1.0

    def test_scale_extreme(self):
        score = self.engine._questionnaire_similarity({"10": 1}, {"10": 5})
        assert score == 0.0

    def test_mixed_types(self):
        score = self.engine._questionnaire_similarity(
            {"1": "yes", "10": 4, "20": "student"},
            {"1": "yes", "10": 3, "20": "student"}
        )
        assert score == pytest.approx((1.0 + 0.75 + 1.0) / 3)

    def test_empty_answers(self):
        score = self.engine._questionnaire_similarity({}, {})
        assert score == 0.5

class TestCompatibilityEngine:
    def test_compute_for_user_no_answers(self, monkeypatch):
        """User with no answers -> skipped."""
        engine = CompatibilityEngine()
        monkeypatch.setattr(engine, "_get_answers_as_dict", lambda uid: {})
        # Mock session.query to return empty lists for all queries
        class FakeAll:
            def all(self): return []
            def first(self): return None
        class FakeFilter:
            def filter(self, *a, **kw): return FakeAll()
            def order_by(self, *a, **kw): return []
        monkeypatch.setattr(engine.session, "query", lambda *a, **kw: FakeFilter())
        result = engine.compute_for_user("user_x")
        assert result["status"] == "skipped"

    def test_pairwise_computation(self):
        engine = CompatibilityEngine()
        score = engine._compute_pairwise(
            {"1": "male", "2": "student"}, {"1": "male", "2": "student"},
            type("obj", (object,), {"gender": "male", "occupation": "student", "birth_year": 2000})(),
            type("obj", (object,), {"gender": "male", "occupation": "student", "birth_year": 2001})(),
        )
        assert score >= 0.9

    def test_gender_mismatch_penalty(self):
        engine = CompatibilityEngine()
        score = engine._compute_pairwise(
            {"1": "yes"}, {"1": "yes"},
            type("obj", (object,), {"gender": "male", "occupation": "student", "birth_year": 2000})(),
            type("obj", (object,), {"gender": "female", "occupation": "student", "birth_year": 2000})(),
        )
        assert score < 1.0

    def test_aggregate_room_score(self):
        engine = CompatibilityEngine()
        score = engine._aggregate_room_score([0.9, 0.8], 2)
        avg = 0.85
        expected = avg * (0.7 + 0.3 * min(1.0, 2/3))
        assert score == pytest.approx(expected)

    def test_aggregate_empty(self):
        engine = CompatibilityEngine()
        assert engine._aggregate_room_score([], 1) == 0.5
