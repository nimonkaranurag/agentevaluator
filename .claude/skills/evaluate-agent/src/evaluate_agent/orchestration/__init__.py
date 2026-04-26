"""
Expand a validated manifest into a deterministic per-case fan-out plan.
"""

from .driver_invocation import DriverInvocation
from .swarm_entry import SwarmEntry
from .swarm_plan import SwarmPlan, plan_swarm

__all__ = [
    "DriverInvocation",
    "SwarmEntry",
    "SwarmPlan",
    "plan_swarm",
]
