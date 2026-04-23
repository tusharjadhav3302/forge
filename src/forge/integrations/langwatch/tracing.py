"""LangWatch tracing integration for LLM observability.

Provides the same interface as the Langfuse integration so both can be
used interchangeably.  LangWatch uses OpenTelemetry under the hood and
offers a LangChain ``BaseCallbackHandler`` that captures LLM calls,
tool use, and agent activity.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_setup_done = False


def _langwatch_enabled() -> bool:
    """Check whether LangWatch is configured via environment."""
    return bool(os.environ.get("LANGWATCH_API_KEY"))


def setup_langwatch() -> None:
    """Initialise the LangWatch SDK (idempotent).

    Reads ``LANGWATCH_API_KEY`` and ``LANGWATCH_ENDPOINT`` from the
    environment.  Must be called once at application startup before any
    traces are created.
    """
    global _setup_done
    if _setup_done or not _langwatch_enabled():
        return

    try:
        import langwatch

        endpoint = os.environ.get("LANGWATCH_ENDPOINT", "http://localhost:5560")
        api_key = os.environ.get("LANGWATCH_API_KEY", "")

        langwatch.setup(
            api_key=api_key,
            endpoint_url=endpoint,
        )
        _setup_done = True
        logger.info(f"LangWatch SDK initialised (endpoint={endpoint})")
    except ImportError:
        logger.warning("langwatch package not installed — tracing disabled")
    except Exception as exc:
        logger.error(f"Failed to initialise LangWatch: {exc}")


def get_langwatch_callback(
    trace_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any | None:
    """Return a LangChain callback handler that sends traces to LangWatch.

    Args:
        trace_name: Optional human-readable name for the trace.
        metadata: Optional metadata dict attached to the trace.

    Returns:
        ``LangChainTracer`` instance, or ``None`` if LangWatch is disabled.
    """
    if not _langwatch_enabled():
        return None

    setup_langwatch()

    try:
        import langwatch
        from langwatch.langchain import LangChainTracer

        trace = langwatch.trace(name=trace_name or "forge")
        if metadata:
            trace.update(metadata=metadata)

        return LangChainTracer(trace=trace)
    except ImportError:
        logger.warning("langwatch package not installed")
        return None
    except Exception as exc:
        logger.error(f"Failed to create LangWatch callback: {exc}")
        return None


def get_langwatch_config(
    trace_name: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a LangChain-compatible config dict with LangWatch callbacks.

    Can be passed directly to ``agent.ainvoke(..., config=config)``.

    Args:
        trace_name: Trace name for the LangWatch dashboard.
        session_id: Session / thread ID (e.g. Jira ticket key).
        metadata: Extra metadata dict.

    Returns:
        Config dict with ``callbacks`` key, or empty dict if disabled.
    """
    meta = dict(metadata or {})
    if session_id:
        meta["thread_id"] = session_id

    handler = get_langwatch_callback(trace_name=trace_name, metadata=meta)
    if handler is None:
        return {}

    return {"callbacks": [handler]}


async def shutdown_langwatch() -> None:
    """Flush pending spans and shut down the LangWatch SDK."""
    if not _setup_done:
        return

    try:
        from opentelemetry.trace import get_tracer_provider

        provider = get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()
        logger.info("LangWatch traces flushed")
    except Exception as exc:
        logger.warning(f"Error flushing LangWatch: {exc}")
