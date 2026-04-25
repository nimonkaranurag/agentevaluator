"""
Swarm orchestration: expand a validated manifest into a deterministic per-case fan-out plan.
"""

from .fanout import (
    DriverInvocation,
    SwarmEntry,
    SwarmPlan,
    plan_swarm,
)

__all__ = [
    "DriverInvocation",
    "SwarmEntry",
    "SwarmPlan",
    "plan_swarm",
]
