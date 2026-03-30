"""Langfuse tracing integration for LLM observability."""

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Generator, Optional

from forge.config import get_settings

logger = logging.getLogger(__name__)

# Langfuse client singleton
_langfuse: Optional[Any] = None


@lru_cache
def get_langfuse() -> Optional[Any]:
    """Get or create the Langfuse client singleton.

    Returns:
        Langfuse client if configured, None otherwise.
    """
    global _langfuse

    settings = get_settings()
    if not settings.langfuse_enabled:
        logger.debug("Langfuse not configured, tracing disabled")
        return None

    if _langfuse is None:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key.get_secret_value(),
                host=settings.langfuse_host,
            )
            logger.info("Langfuse client initialized")
        except ImportError:
            logger.warning("Langfuse package not installed, tracing disabled")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            return None

    return _langfuse


@contextmanager
def trace_llm_call(
    name: str,
    input_data: dict[str, Any],
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager for tracing LLM calls with Langfuse.

    Args:
        name: Name of the LLM operation.
        input_data: Input data for the LLM call.
        metadata: Optional additional metadata.

    Yields:
        Dict to capture output data (modify in place).

    Example:
        with trace_llm_call("generate_prd", {"raw_text": text}) as trace:
            result = await claude.generate(...)
            trace["output"] = result
    """
    langfuse = get_langfuse()
    output_data: dict[str, Any] = {}

    if langfuse is None:
        # No-op when Langfuse is not configured
        yield output_data
        return

    trace = None
    generation = None

    try:
        trace = langfuse.trace(name=name, metadata=metadata or {})
        generation = trace.generation(name=f"{name}_generation", input=input_data)

        yield output_data

        # Complete the generation with output
        if generation:
            generation.end(output=output_data.get("output"))

    except Exception as e:
        logger.error(f"Langfuse tracing error: {e}")
        if generation:
            generation.end(
                output={"error": str(e)},
                status_message=str(e),
            )
        raise
    finally:
        # Flush traces
        if langfuse:
            try:
                langfuse.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse traces: {e}")


async def shutdown_langfuse() -> None:
    """Shutdown the Langfuse client and flush remaining traces."""
    global _langfuse

    if _langfuse is not None:
        try:
            _langfuse.flush()
            _langfuse.shutdown()
            logger.info("Langfuse client shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down Langfuse: {e}")
        finally:
            _langfuse = None
