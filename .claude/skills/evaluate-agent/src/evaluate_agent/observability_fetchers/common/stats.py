"""
Single-pass aggregation of canonical Generation records into FetchedObservability stats.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from evaluate_agent.scoring.observability.schema import (
    Generation,
)


@dataclass(frozen=True)
class GenerationStats:
    with_tokens: int
    with_cost: int
    with_interval: int
    total_tokens: int | None
    total_cost_usd: float | None


def aggregate_generation_stats(
    generations: Iterable[Generation],
) -> GenerationStats:
    # The None-vs-zero distinction is load-bearing: total_tokens
    # stays None until at least one generation contributes a
    # value. "No usage data captured" and "zero tokens used" are
    # different states downstream — the former resolves the
    # corresponding assertion to inconclusive, the latter to
    # passed/failed against the declared cap.
    with_tokens = 0
    with_cost = 0
    with_interval = 0
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    for generation in generations:
        if generation.total_tokens is not None:
            with_tokens += 1
            total_tokens = (
                generation.total_tokens
                if total_tokens is None
                else total_tokens + generation.total_tokens
            )
        if generation.total_cost_usd is not None:
            with_cost += 1
            total_cost_usd = (
                generation.total_cost_usd
                if total_cost_usd is None
                else total_cost_usd
                + generation.total_cost_usd
            )
        if (
            generation.started_at is not None
            and generation.ended_at is not None
        ):
            with_interval += 1
    return GenerationStats(
        with_tokens=with_tokens,
        with_cost=with_cost,
        with_interval=with_interval,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
    )


__all__ = ["GenerationStats", "aggregate_generation_stats"]
