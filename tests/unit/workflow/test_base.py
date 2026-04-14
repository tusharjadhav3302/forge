"""Tests for BaseState and mixins."""

import pytest
from typing import get_type_hints


class TestBaseState:
    """Tests for BaseState TypedDict."""

    def test_base_state_has_required_fields(self):
        """BaseState includes all shared workflow fields."""
        from forge.workflow.base import BaseState

        hints = get_type_hints(BaseState)

        # Identity fields
        assert "thread_id" in hints
        assert "ticket_key" in hints

        # Execution control
        assert "current_node" in hints
        assert "is_paused" in hints
        assert "retry_count" in hints
        assert "last_error" in hints

        # Timestamps
        assert "created_at" in hints
        assert "updated_at" in hints

        # Feedback
        assert "feedback_comment" in hints
        assert "revision_requested" in hints

    def test_base_state_is_total_false(self):
        """BaseState allows partial initialization."""
        from forge.workflow.base import BaseState

        # Should not raise - all fields optional
        state: BaseState = {"thread_id": "test", "ticket_key": "TEST-1"}
        assert state["thread_id"] == "test"


class TestPRIntegrationState:
    """Tests for PR integration mixin."""

    def test_pr_state_has_required_fields(self):
        """PRIntegrationState includes PR-related fields."""
        from forge.workflow.base import PRIntegrationState

        hints = get_type_hints(PRIntegrationState)

        assert "workspace_path" in hints
        assert "pr_urls" in hints
        assert "current_pr_url" in hints
        assert "current_repo" in hints
        assert "repos_to_process" in hints
        assert "repos_completed" in hints


class TestCIIntegrationState:
    """Tests for CI integration mixin."""

    def test_ci_state_has_required_fields(self):
        """CIIntegrationState includes CI-related fields."""
        from forge.workflow.base import CIIntegrationState

        hints = get_type_hints(CIIntegrationState)

        assert "ci_status" in hints
        assert "ci_failed_checks" in hints
        assert "ci_fix_attempts" in hints


class TestReviewIntegrationState:
    """Tests for review integration mixin."""

    def test_review_state_has_required_fields(self):
        """ReviewIntegrationState includes review-related fields."""
        from forge.workflow.base import ReviewIntegrationState

        hints = get_type_hints(ReviewIntegrationState)

        assert "ai_review_status" in hints
        assert "ai_review_results" in hints
        assert "human_review_status" in hints
        assert "pr_merged" in hints
