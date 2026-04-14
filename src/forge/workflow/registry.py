"""Default workflow registry."""

from forge.workflow.bug import BugWorkflow
from forge.workflow.feature import FeatureWorkflow
from forge.workflow.router import WorkflowRouter


def create_default_router() -> WorkflowRouter:
    """Create router with built-in workflows."""
    router = WorkflowRouter()
    router.register(FeatureWorkflow)
    router.register(BugWorkflow)
    return router
