"""Prometheus metrics endpoint for observability."""

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

router = APIRouter(tags=["metrics"])

# Webhook counters
WEBHOOKS_RECEIVED = Counter(
    "forge_webhooks_received_total",
    "Total number of webhook events received",
    ["source", "event_type"],
)

WEBHOOKS_PROCESSED = Counter(
    "forge_webhooks_processed_total",
    "Total number of webhook events successfully processed",
    ["source", "event_type"],
)

WEBHOOKS_FAILED = Counter(
    "forge_webhooks_failed_total",
    "Total number of webhook events that failed processing",
    ["source", "event_type", "error_type"],
)

# Workflow counters
WORKFLOWS_STARTED = Counter(
    "forge_workflows_started_total",
    "Total number of workflows started",
    ["ticket_type"],
)

WORKFLOWS_COMPLETED = Counter(
    "forge_workflows_completed_total",
    "Total number of workflows completed",
    ["ticket_type", "final_node"],
)

WORKFLOWS_FAILED = Counter(
    "forge_workflows_failed_total",
    "Total number of workflows that failed",
    ["ticket_type", "error_type"],
)

# CI/CD metrics
CI_FIX_ATTEMPTS = Counter(
    "forge_ci_fix_attempts_total",
    "Total number of CI fix attempts",
    ["repo", "result"],
)

# Agent metrics
AGENT_INVOCATIONS = Counter(
    "forge_agent_invocations_total",
    "Total number of agent invocations",
    ["task_type"],
)

AGENT_DURATION = Histogram(
    "forge_agent_duration_seconds",
    "Duration of agent invocations",
    ["task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "forge_queue_depth",
    "Current depth of event queues",
    ["queue_name"],
)

# MCP metrics
MCP_TOOLS_LOADED = Gauge(
    "forge_mcp_tools_loaded",
    "Number of MCP tools currently loaded",
    ["server"],
)


@router.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics.

    Returns:
        Prometheus-formatted metrics.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Helper functions to record metrics
def record_webhook_received(source: str, event_type: str) -> None:
    """Record a webhook received event."""
    WEBHOOKS_RECEIVED.labels(source=source, event_type=event_type).inc()


def record_webhook_processed(source: str, event_type: str) -> None:
    """Record a webhook successfully processed."""
    WEBHOOKS_PROCESSED.labels(source=source, event_type=event_type).inc()


def record_webhook_failed(source: str, event_type: str, error_type: str) -> None:
    """Record a webhook processing failure."""
    WEBHOOKS_FAILED.labels(source=source, event_type=event_type, error_type=error_type).inc()


def record_workflow_started(ticket_type: str) -> None:
    """Record a workflow started."""
    WORKFLOWS_STARTED.labels(ticket_type=ticket_type).inc()


def record_workflow_completed(ticket_type: str, final_node: str) -> None:
    """Record a workflow completed."""
    WORKFLOWS_COMPLETED.labels(ticket_type=ticket_type, final_node=final_node).inc()


def record_workflow_failed(ticket_type: str, error_type: str) -> None:
    """Record a workflow failure."""
    WORKFLOWS_FAILED.labels(ticket_type=ticket_type, error_type=error_type).inc()


def record_ci_fix_attempt(repo: str, result: str) -> None:
    """Record a CI fix attempt."""
    CI_FIX_ATTEMPTS.labels(repo=repo, result=result).inc()


def record_agent_invocation(task_type: str) -> None:
    """Record an agent invocation."""
    AGENT_INVOCATIONS.labels(task_type=task_type).inc()


def observe_agent_duration(task_type: str, duration: float) -> None:
    """Record agent invocation duration."""
    AGENT_DURATION.labels(task_type=task_type).observe(duration)


def set_queue_depth(queue_name: str, depth: int) -> None:
    """Set current queue depth."""
    QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)


def set_mcp_tools_loaded(server: str, count: int) -> None:
    """Set number of MCP tools loaded from a server."""
    MCP_TOOLS_LOADED.labels(server=server).set(count)
