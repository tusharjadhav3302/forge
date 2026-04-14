"""Default workflow registry."""

from forge.workflow.router import WorkflowRouter
from forge.workflow.feature import FeatureWorkflow
from forge.workflow.bug import BugWorkflow


def create_default_router() -> WorkflowRouter:
    """Create router with built-in workflows."""
    router = WorkflowRouter()
    router.register(FeatureWorkflow)
    router.register(BugWorkflow)
    return router
