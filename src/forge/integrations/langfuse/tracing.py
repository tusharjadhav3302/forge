"""Langfuse tracing integration for LLM observability."""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

from forge.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def trace_llm_call(
    name: str,
    input_data: dict[str, Any],
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager for tracing LLM calls with Langfuse.

    This is a no-op wrapper that allows code to execute without tracing.
    Langfuse integration is disabled until API compatibility is resolved.

    Args:
        name: Name of the LLM operation.
        input_data: Input data for the LLM call.
        metadata: Optional additional metadata.

    Yields:
        Dict to capture output data (modify in place).
    """
    output_data: dict[str, Any] = {}
    # Simply yield and let the code execute - no tracing for now
    yield output_data


async def shutdown_langfuse() -> None:
    """Shutdown the Langfuse client (no-op when disabled)."""
    pass
