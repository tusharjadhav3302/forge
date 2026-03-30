"""Langfuse tracing integration for LLM observability."""

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, Optional

from forge.config import get_settings

logger = logging.getLogger(__name__)

# Flag to track if env vars are set
_env_configured = False


def _ensure_langfuse_env() -> bool:
    """Ensure Langfuse environment variables are set.

    Returns:
        True if Langfuse is enabled and configured.
    """
    global _env_configured

    settings = get_settings()
    if not settings.langfuse_enabled:
        return False

    if not _env_configured:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault(
            "LANGFUSE_SECRET_KEY", settings.langfuse_secret_key.get_secret_value()
        )
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
        _env_configured = True

    return True


def get_langfuse_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[Any]:
    """Get a Langfuse callback handler for LangChain/LangGraph.

    Creates a new handler instance with optional session tracking.
    Use session_id to group all traces for a ticket together.

    Args:
        session_id: Session ID to group traces (e.g., ticket key).
        user_id: Optional user ID for attribution.
        tags: Optional tags for filtering.

    Returns:
        CallbackHandler instance or None if disabled.
    """
    if not _ensure_langfuse_env():
        return None

    try:
        from langfuse.callback import CallbackHandler

        handler = CallbackHandler(
            session_id=session_id,
            user_id=user_id,
            tags=tags,
        )
        if session_id:
            logger.debug(f"Langfuse handler created for session: {session_id}")
        return handler

    except ImportError:
        logger.warning(
            "langfuse package not installed. Install with: pip install langfuse"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse handler: {e}")
        return None


def get_langfuse_config(
    trace_name: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Get a LangChain config dict with Langfuse callback.

    This can be passed directly to agent.invoke() or chain.invoke().
    Each call creates a new handler with the specified session_id,
    allowing traces to be grouped by ticket/session.

    Args:
        trace_name: Optional name for the trace.
        user_id: Optional user ID for the trace.
        session_id: Optional session ID to group traces (e.g., ticket key).
        tags: Optional list of tags.
        metadata: Optional additional metadata.

    Returns:
        Config dict with callbacks and metadata, or empty dict if disabled.
    """
    # Create a handler with session tracking
    handler = get_langfuse_handler(
        session_id=session_id,
        user_id=user_id,
        tags=tags,
    )
    if handler is None:
        return {}

    config: dict[str, Any] = {"callbacks": [handler]}

    # Build metadata for trace name and additional data
    langfuse_metadata: dict[str, Any] = {}
    if trace_name:
        langfuse_metadata["langfuse_trace_name"] = trace_name
    if metadata:
        langfuse_metadata.update(metadata)

    if langfuse_metadata:
        config["metadata"] = langfuse_metadata

    return config


@contextmanager
def trace_llm_call(
    name: str,
    input_data: dict[str, Any],
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager for tracing LLM calls with Langfuse.

    Note: For LangChain/Deep Agents, use get_langfuse_config() instead
    and pass the callbacks via the config parameter.

    This context manager is kept for backwards compatibility with
    direct Anthropic API calls.

    Args:
        name: Name of the LLM operation.
        input_data: Input data for the LLM call.
        metadata: Optional additional metadata.

    Yields:
        Dict to capture output data (modify in place).
    """
    import os

    settings = get_settings()
    output_data: dict[str, Any] = {}

    if not settings.langfuse_enabled:
        yield output_data
        return

    try:
        from langfuse import Langfuse

        # Langfuse v4+ reads config from environment variables
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault(
            "LANGFUSE_SECRET_KEY", settings.langfuse_secret_key.get_secret_value()
        )
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

        langfuse = Langfuse()

        trace = langfuse.trace(name=name, input=input_data, metadata=metadata)
        generation = trace.generation(name=f"{name}_generation", input=input_data)

        yield output_data

        generation.end(output=output_data.get("output"))
        langfuse.flush()

    except ImportError:
        logger.debug("Langfuse not installed, skipping tracing")
        yield output_data
    except Exception as e:
        logger.warning(f"Langfuse tracing error: {e}")
        yield output_data


async def shutdown_langfuse() -> None:
    """Shutdown the Langfuse client and flush pending traces."""
    global _langfuse_handler

    if _langfuse_handler is not None:
        try:
            from langfuse import get_client

            client = get_client()
            client.flush()
            logger.info("Langfuse traces flushed")
        except Exception as e:
            logger.warning(f"Error flushing Langfuse: {e}")
        finally:
            _langfuse_handler = None
