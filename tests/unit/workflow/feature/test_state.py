"""Tests for FeatureState."""

from typing import get_type_hints


class TestFeatureState:
    """Tests for FeatureState TypedDict."""

    def test_feature_state_inherits_base_state(self):
        """FeatureState includes BaseState fields."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        # BaseState fields
        assert "thread_id" in hints
        assert "ticket_key" in hints
        assert "current_node" in hints

    def test_feature_state_has_artifact_fields(self):
        """FeatureState includes PRD and spec content."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "prd_content" in hints
        assert "spec_content" in hints

    def test_feature_state_has_epic_task_tracking(self):
        """FeatureState includes epic and task tracking."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "epic_keys" in hints
        assert "task_keys" in hints
        assert "tasks_by_repo" in hints

    def test_feature_state_has_pr_fields(self):
        """FeatureState includes PR integration fields."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "workspace_path" in hints
        assert "pr_urls" in hints

    def test_create_initial_feature_state(self):
        """Can create initial feature state."""
        from forge.workflow.feature.state import create_initial_feature_state

        state = create_initial_feature_state("TEST-123")

        assert state["ticket_key"] == "TEST-123"
        assert state["prd_content"] == ""
        assert state["epic_keys"] == []
