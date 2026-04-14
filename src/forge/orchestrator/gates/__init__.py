"""Gate implementations - DEPRECATED, use forge.workflow.gates directly.

This module is maintained for backward compatibility only.
New code should import directly from forge.workflow.gates.
"""

import warnings

warnings.warn(
    "forge.orchestrator.gates is deprecated. Use forge.workflow.gates directly.",
    DeprecationWarning,
    stacklevel=2,
)

from forge.workflow.gates.plan_approval import (
    plan_approval_gate,
    route_plan_approval,
)
from forge.workflow.gates.prd_approval import (
    prd_approval_gate,
    route_prd_approval,
)
from forge.workflow.gates.spec_approval import (
    route_spec_approval,
    spec_approval_gate,
)
from forge.workflow.gates.task_approval import (
    route_task_approval,
    task_approval_gate,
)

__all__ = [
    "prd_approval_gate",
    "route_prd_approval",
    "route_spec_approval",
    "spec_approval_gate",
    "plan_approval_gate",
    "route_plan_approval",
    "route_task_approval",
    "task_approval_gate",
]
