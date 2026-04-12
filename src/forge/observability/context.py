"""Trace context propagation with correlation IDs."""

import contextvars
import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from opentelemetry import trace

logger = logging.getLogger(__name__)

# Context variable for correlation ID
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="",
)

# Context variable for workflow metadata
_workflow_context: contextvars.ContextVar[Optional["WorkflowTraceContext"]] = (
    contextvars.ContextVar("workflow_context", default=None)
)


@dataclass
class WorkflowTraceContext:
    """Context for workflow tracing metadata."""

    ticket_key: str
    workflow_phase: str
    repository: str | None = None
    pr_number: int | None = None

    def to_attributes(self) -> dict:
        """Convert to span attributes."""
        attrs = {
            "forge.ticket_key": self.ticket_key,
            "forge.workflow_phase": self.workflow_phase,
        }
        if self.repository:
            attrs["forge.repository"] = self.repository
        if self.pr_number:
            attrs["forge.pr_number"] = self.pr_number
        return attrs


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        UUID-based correlation ID string.
    """
    return str(uuid.uuid4())


def get_correlation_id() -> str:
    """Get the current correlation ID.

    Returns:
        Current correlation ID or empty string if not set.
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: The correlation ID to set.

    Returns:
        Token for resetting to previous value.
    """
    return _correlation_id.set(correlation_id)


def get_workflow_context() -> WorkflowTraceContext | None:
    """Get the current workflow trace context.

    Returns:
        Current workflow context or None if not set.
    """
    return _workflow_context.get()


def set_workflow_context(context: WorkflowTraceContext) -> contextvars.Token:
    """Set the workflow trace context.

    Args:
        context: Workflow context to set.

    Returns:
        Token for resetting to previous value.
    """
    return _workflow_context.set(context)


class CorrelationContext:
    """Context manager for correlation ID propagation.

    Usage:
        async with CorrelationContext(request_id="abc123"):
            # All operations here will have correlation_id set
            await process_request()
    """

    def __init__(
        self,
        correlation_id: str | None = None,
        ticket_key: str | None = None,
        workflow_phase: str | None = None,
        repository: str | None = None,
    ):
        """Initialize correlation context.

        Args:
            correlation_id: Correlation ID (generated if not provided).
            ticket_key: Jira ticket key for workflow context.
            workflow_phase: Current workflow phase.
            repository: Repository being worked on.
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.ticket_key = ticket_key
        self.workflow_phase = workflow_phase
        self.repository = repository
        self._correlation_token: contextvars.Token | None = None
        self._workflow_token: contextvars.Token | None = None

    def __enter__(self) -> "CorrelationContext":
        """Enter context and set correlation ID."""
        self._correlation_token = set_correlation_id(self.correlation_id)

        if self.ticket_key and self.workflow_phase:
            workflow_ctx = WorkflowTraceContext(
                ticket_key=self.ticket_key,
                workflow_phase=self.workflow_phase,
                repository=self.repository,
            )
            self._workflow_token = set_workflow_context(workflow_ctx)

        # Add to current span if active
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("correlation_id", self.correlation_id)
            if self.ticket_key:
                span.set_attribute("forge.ticket_key", self.ticket_key)
            if self.workflow_phase:
                span.set_attribute("forge.workflow_phase", self.workflow_phase)
            if self.repository:
                span.set_attribute("forge.repository", self.repository)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and reset correlation ID."""
        if self._correlation_token is not None:
            _correlation_id.reset(self._correlation_token)
        if self._workflow_token is not None:
            _workflow_context.reset(self._workflow_token)

    async def __aenter__(self) -> "CorrelationContext":
        """Async enter context."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit context."""
        self.__exit__(exc_type, exc_val, exc_tb)


def add_trace_metadata(
    ticket_key: str | None = None,
    workflow_phase: str | None = None,
    repository: str | None = None,
    **extra_attributes,
) -> None:
    """Add metadata to the current span.

    Adds forge-specific attributes to the active span for
    correlation and filtering in trace backends.

    Args:
        ticket_key: Jira ticket key.
        workflow_phase: Current workflow phase.
        repository: Repository being worked on.
        **extra_attributes: Additional span attributes.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return

    correlation_id = get_correlation_id()
    if correlation_id:
        span.set_attribute("correlation_id", correlation_id)

    if ticket_key:
        span.set_attribute("forge.ticket_key", ticket_key)
    if workflow_phase:
        span.set_attribute("forge.workflow_phase", workflow_phase)
    if repository:
        span.set_attribute("forge.repository", repository)

    for key, value in extra_attributes.items():
        span.set_attribute(f"forge.{key}", value)
