#!/usr/bin/env python3
"""Patch specific fields in a workflow checkpoint state.

Usage:
    uv run python scripts/patch_checkpoint.py AISOS-358 fork_owner=eshulman2 fork_repo=installer
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def patch(ticket_key: str, patches: dict) -> None:
    from forge.models.workflow import TicketType
    from forge.orchestrator.checkpointer import get_checkpointer
    from forge.workflow.registry import create_default_router

    checkpointer = await get_checkpointer()

    router = create_default_router()
    workflow_instance = router.resolve(ticket_type=TicketType.FEATURE, labels=[], event={})
    graph = workflow_instance.build_graph()
    compiled = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": ticket_key}}

    state = await compiled.aget_state(config)
    if not state or not state.values:
        print(f"No checkpoint found for {ticket_key}")
        return

    print(f"Current state fields relevant to patch:")
    for k in patches:
        print(f"  {k}: {state.values.get(k)!r}")

    await compiled.aupdate_state(config, patches)

    # Verify
    updated = await compiled.aget_state(config)
    print(f"\nPatched successfully:")
    for k, v in patches.items():
        print(f"  {k}: {updated.values.get(k)!r}")


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: patch_checkpoint.py <ticket_key> <field=value> [field=value ...]")
        print("Example: patch_checkpoint.py AISOS-358 fork_owner=eshulman2 fork_repo=installer")
        sys.exit(1)

    ticket_key = sys.argv[1]
    patches: dict = {}

    for arg in sys.argv[2:]:
        if "=" not in arg:
            print(f"Invalid argument (expected field=value): {arg}")
            sys.exit(1)
        field, _, raw_value = arg.partition("=")
        # Try to parse as JSON for booleans/numbers, fall back to string
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        patches[field] = value

    asyncio.run(patch(ticket_key, patches))


if __name__ == "__main__":
    main()
