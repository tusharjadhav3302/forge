"""Claude/Anthropic integration for AI code generation."""

from forge.integrations.claude.agent import DeepAgentClient

# Backwards compatibility alias
ClaudeAgentClient = DeepAgentClient

__all__ = ["DeepAgentClient", "ClaudeAgentClient"]
