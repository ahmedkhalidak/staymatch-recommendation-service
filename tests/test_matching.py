"""Unit tests for CompatibilityEngine and feature_encoding."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.matching.feature_encoding import weighted_similarity, sim
# Import CompatibilityEngine without patching - tests will mock as needed
from app.services.matching.compatibility_engine import CompatibilityEngine


class TestWeightedSimilarity:
    """Tests for the standalone weighted_similarity function with dynamic weights."""

    def setup_method(self):
        # Setup mock weights and metadata for testing
        self.weights = {
            1: 0.03, 2: 0.05, 3: 0.05, 4: 0.10, 5: 0.14,
            6: 0.04, 7: 0.14, 8: 0.03, 9: 0.07, 10: 0.08,
            11: 0.14, 12: 0.05, 13: 0.08,
        }
        self.metadata = {
            qid: {
                "question_type": "categorical",
                "options_en": ["opt1", "opt2", "opt3", "opt4"],
                "options_ar": ["opt1", "opt2", "opt3", "opt4"],
                "weight": self.weights[qid],
                "question_en": f"Question {qid}",
                "question_ar": f"سؤال {qid}",
            }
            for qid in self.weights.keys()
        }
        # Question 11 is smoking
        self.metadata[11]["question_en"] = "Smoking preference?"
        self.metadata[11]["question_ar"] = "موقفك من التدخين؟"
        self.smoking_qid = 11

    def test_same_answers(self):
        score = weighted_similarity(
            {"1": 0, "2": 0}, {"1": 0, "2": 0},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score == pytest.approx(1.0)

    def test_completely_different(self):
        score = weighted_similarity(
            {"7": 0}, {"7": 3},
            self.weights, self.metadata, self.smoking_qid
        )
        w = self.weights[7]
        expected = (w * 0.0) / w  # Categorical: exact match required
        assert score == pytest.approx(expected)

    def test_no_shared_questions(self):
        score = weighted_similarity(
            {"1": "yes"}, {"2": "no"},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score == 0.5

    def test_empty_answers(self):
        score = weighted_similarity(
            {}, {},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score == 0.5

    def test_smoking_penalty(self):
        score = weighted_similarity(
            {"11": 0}, {"11": 3},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score < 0.5

    def test_smoking_same(self):
        score = weighted_similarity(
            {"11": 0}, {"11": 0},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score == 1.0

    def test_smoking_close(self):
        score = weighted_similarity(
            {"11": 1}, {"11": 2},
            self.weights, self.metadata, self.smoking_qid
        )
        assert score == 1.0

    def test_smoking_opposite(self):
        score = weighted_similarity(
            {"11": 0}, {"11": 3},
            self.weights, self.metadata, self.smoking_qid
        )
        # Smoking distance 3 -> similarity 0.0, penalty 0.3
        w = self.weights[11]
        expected = 0.0 * 0.3
        assert score == pytest.approx(expected)

