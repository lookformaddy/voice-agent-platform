"""Per-session configuration. All values are explicit and validated so a
misconfigured session fails at construction, not mid-conversation."""

from __future__ import annotations

from dataclasses import dataclass, field


class InterruptionPolicy:
    """Barge-in behaviour while the agent is speaking."""

    ALLOW = "allow"  # interruption cancels in-flight synthesis
    IGNORE = "ignore"  # interruption is noted but speech continues


@dataclass(frozen=True)
class LatencyBudgets:
    """Latency budgets in milliseconds. A breach is flagged, never dropped."""

    first_audio_ms: float = 800.0
    end_of_turn_ms: float = 5000.0
    interruption_response_ms: float = 300.0


@dataclass(frozen=True)
class SessionConfig:
    voice: str = "default"
    language: str = "en-US"
    interruption_policy: str = InterruptionPolicy.ALLOW
    latency_budgets: LatencyBudgets = field(default_factory=LatencyBudgets)
    max_memory_turns: int = 10
    max_memory_tokens: int = 2000
    tool_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.interruption_policy not in (
            InterruptionPolicy.ALLOW,
            InterruptionPolicy.IGNORE,
        ):
            raise ValueError(f"unknown interruption policy: {self.interruption_policy}")
        if self.max_memory_turns < 1 or self.max_memory_tokens < 1:
            raise ValueError("memory budgets must be positive")
        if self.tool_timeout_seconds <= 0:
            raise ValueError("tool timeout must be positive")
