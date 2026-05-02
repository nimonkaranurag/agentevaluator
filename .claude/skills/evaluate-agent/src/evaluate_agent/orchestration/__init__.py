"""
Expand a validated manifest into a deterministic per-case fan-out plan.
"""

from .case_directive import CaseDirective
from .swarm_plan import SwarmPlan, plan_swarm

__all__ = [
    "CaseDirective",
    "SwarmPlan",
    "plan_swarm",
]
