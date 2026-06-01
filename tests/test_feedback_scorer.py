"""Unit tests for FeedbackScorer (boost/penalty logic)."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.scoring.feedback_scorer import FeedbackScorer

class TestFeedbackScorer:
    def test_default_boost(self):
        """No feedback data → boost = 1.0"""
        scorer = FeedbackScorer()
        mock_repo = MagicMock()
        mock_repo.get_user_feedback.return_value = None
        scorer.feedback_repo = mock_repo
        assert scorer.compute_boost("user_x", 1) == 1.0

    def test_custom_boost(self):
        """Existing feedback boost → returns it"""
        scorer = FeedbackScorer()
        mock_feedback = MagicMock(boost_factor=1.5)
        mock_repo = MagicMock()
        mock_repo.get_user_feedback.return_value = mock_feedback
        scorer.feedback_repo = mock_repo
        assert scorer.compute_boost("user_x", 1) == 1.5

    def test_penalty_boost(self):
        """Negative feedback → low boost factor"""
        scorer = FeedbackScorer()
        mock_feedback = MagicMock(boost_factor=0.6)
        mock_repo = MagicMock()
        mock_repo.get_user_feedback.return_value = mock_feedback
        scorer.feedback_repo = mock_repo
        assert scorer.compute_boost("user_x", 1) == 0.6
