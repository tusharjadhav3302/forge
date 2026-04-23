# Proposal: LangWatch Integration as Optional Observability Backend

**Author:** Tushar Jadhav
**Date:** 2026-04-22
**Status:** Under Review

## Summary

Add LangWatch as an optional, parallel observability backend alongside the existing Langfuse integration. LangWatch provides OTLP-native LLM tracing, 30+ built-in evaluators (RAGAS, safety, PII detection), agent simulation, and prompt management with Git sync — capabilities that directly support Forge's AI quality metrics needs.

## Motivation

### Problem Statement

Forge currently integrates only with Langfuse for LLM observability. While Langfuse provides solid trace capture and cost tracking, it lacks built-in evaluation capabilities. Teams needing to measure AI output quality (faithfulness, BLEU/ROUGE scores, PII detection, content safety) must build custom evaluation pipelines and post scores manually via the Langfuse API.

### Current Workarounds

- Quality metrics like faithfulness and RAGAS scores require writing standalone evaluation scripts and posting results back to Langfuse via `langfuse.score()`.
- There is no built-in agent simulation capability for end-to-end workflow testing.
- Safety evaluations (prompt injection, PII, content moderation) require integrating separate third-party services.

## Proposal

### Overview

Introduce a `forge/integrations/langwatch/` module that mirrors the existing Langfuse integration pattern. Both backends can be enabled simultaneously — their LangChain callbacks are merged into a single list at runtime. LangWatch is disabled by default and requires no new mandatory dependencies.

### Detailed Design

**New module:** `src/forge/integrations/langwatch/`
- `__init__.py` — public API exports
- `tracing.py` — `setup_langwatch()`, `get_langwatch_callback()`, `get_langwatch_config()`, `shutdown_langwatch()`

**Modified modules:**
- `config.py` — three new settings: `LANGWATCH_ENABLED`, `LANGWATCH_API_KEY`, `LANGWATCH_ENDPOINT`
- `integrations/agents/agent.py` — `_run_agent()` collects callbacks from both Langfuse and LangWatch into a unified list
- `main.py` — API server calls `setup_langwatch()` during lifespan startup
- `orchestrator/worker.py` — worker calls `setup_langwatch()` at boot
- `sandbox/runner.py` — passes `LANGWATCH_API_KEY` and `LANGWATCH_ENDPOINT` into containers

**Configuration:** `.env.example` updated with documented LangWatch settings. Developer guide updated with setup instructions.

### User Experience

```bash
# Self-host LangWatch
git clone https://github.com/langwatch/langwatch.git
cd langwatch && docker compose up -d

# Configure in Forge .env
LANGWATCH_ENABLED=true
LANGWATCH_API_KEY=your-key-from-dashboard
LANGWATCH_ENDPOINT=http://localhost:5560

# Restart worker — traces appear at http://localhost:5560
uv run forge worker
```

## Alternatives Considered

| Alternative | Pros | Cons | Why Not |
|-------------|------|------|---------|
| Langfuse only + custom eval scripts | Already integrated, no new code | No built-in evaluators, no agent simulation, manual scoring | Doesn't scale for the quality metrics Forge needs |
| Replace Langfuse with LangWatch | Single backend, simpler | Breaks existing setups, loses Langfuse-specific features | Disruptive; both can coexist |
| OpenTelemetry direct export | Standard protocol | No LLM-specific UI, no evaluators, no prompt management | Too low-level for LLM observability |

## Implementation Plan

### Phases

1. **Phase 1:** Integration module + config + agent wiring — 1 day (this PR)
2. **Phase 2:** Container entrypoint LangWatch support (auto-setup inside containers) — follow-up
3. **Phase 3:** Built-in evaluator hooks (auto-run RAGAS/safety evals on traces) — follow-up

### Dependencies

- [x] `langwatch` Python SDK (pip install langwatch)
- [x] Self-hosted or cloud LangWatch instance
- [ ] No changes to existing Langfuse integration

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK compatibility issues with Python 3.11-3.13 | Low | Med | SDK supports 3.10-3.13; tested locally |
| Callback ordering conflicts with Langfuse | Low | Low | Callbacks are independent handlers in a list |
| LangWatch project maturity | Med | Low | Langfuse remains the default; LangWatch is opt-in |

## Open Questions

- [ ] Should LangWatch SDK be added to `pyproject.toml` dependencies or remain an optional install?
- [ ] Should the container entrypoint also support LangWatch auto-setup (Phase 2)?
- [ ] Should we add a unified observability config that picks one backend vs. both?

## References

- [LangWatch GitHub](https://github.com/langwatch/langwatch)
- [LangWatch Python SDK](https://pypi.org/project/langwatch/)
- [Existing Langfuse integration](../src/forge/integrations/langfuse/tracing.py)
- [Forge proposals template](TEMPLATE.md)
