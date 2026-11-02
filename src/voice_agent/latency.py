"""Latency budget tracking. Breaches are recorded and surfaced in the
session metrics summary; they are never silently dropped."""

from __future__ import annotations

from dataclasses import dataclass, field

from voice_agent.config import LatencyBudgets


@dataclass
class LatencyBreach:
    metric: str
    value_ms: float
    budget_ms: float

    def __str__(self) -> str:
        return (
            f"{self.metric} {self.value_ms:.1f}ms exceeded budget "
            f"{self.budget_ms:.1f}ms"
        )


@dataclass
class LatencyTracker:
    budgets: LatencyBudgets = field(default_factory=LatencyBudgets)
    first_audio_ms: list[float] = field(default_factory=list)
    end_of_turn_ms: list[float] = field(default_factory=list)
    interruption_ms: list[float] = field(default_factory=list)
    breaches: list[LatencyBreach] = field(default_factory=list)

    def _check(self, metric: str, value: float, budget: float) -> None:
        if value > budget:
            self.breaches.append(
                LatencyBreach(metric=metric, value_ms=value, budget_ms=budget)
            )

    def record_first_audio(self, value_ms: float) -> None:
        self.first_audio_ms.append(value_ms)
        self._check("first_audio", value_ms, self.budgets.first_audio_ms)

    def record_end_of_turn(self, value_ms: float) -> None:
        self.end_of_turn_ms.append(value_ms)
        self._check("end_of_turn", value_ms, self.budgets.end_of_turn_ms)

    def record_interruption(self, value_ms: float) -> None:
        self.interruption_ms.append(value_ms)
        self._check(
            "interruption_response", value_ms, self.budgets.interruption_response_ms
        )

    @staticmethod
    def _avg(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None
