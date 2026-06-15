"""Unit tests for FeedbackScorer (boost/penalty logic)."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.scoring.feedback_scorer import FeedbackScorer


class TestFeedbackScorer:
    @patch("app.services.scoring.feedback_scorer.get_session")
    @patch("app.services.scoring.feedback_scorer.FeedbackRepository")
    def test_default_boost(self, mock_repo_cls, mock_session):
        """No feedback data → boost = 1.0"""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_user_feedback.return_value = None
        scorer = FeedbackScorer()
        assert scorer.compute_boost("user_x", 1) == 1.0

    @patch("app.services.scoring.feedback_scorer.get_session")
    @patch("app.services.scoring.feedback_scorer.FeedbackRepository")
    def test_custom_boost(self, mock_repo_cls, mock_session):
        """Existing feedback boost → returns it"""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_feedback = MagicMock(boost_factor=1.5)
        mock_repo.get_user_feedback.return_value = mock_feedback
        scorer = FeedbackScorer()
        assert scorer.compute_boost("user_x", 1) == 1.5

    @patch("app.services.scoring.feedback_scorer.get_session")
    @patch("app.services.scoring.feedback_scorer.FeedbackRepository")
    def test_penalty_boost(self, mock_repo_cls, mock_session):
        """Negative feedback → low boost factor"""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_feedback = MagicMock(boost_factor=0.6)
        mock_repo.get_user_feedback.return_value = mock_feedback
        scorer = FeedbackScorer()
        assert scorer.compute_boost("user_x", 1) == 0.6
