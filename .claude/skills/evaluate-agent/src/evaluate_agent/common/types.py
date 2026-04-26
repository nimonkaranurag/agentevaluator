"""
Frozen + extra-forbidden pydantic base used by every contract type in this skill.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictFrozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


__all__ = ["StrictFrozen"]
