"""Session metrics summary: one dict, safe to log or expose via API."""

from __future__ import annotations

from dataclasses import dataclass, field

from voice_agent.latency import LatencyTracker


@dataclass
class SessionMetrics:
    turns: int = 0
    interruptions: int = 0
    tool_calls: int = 0
    tool_successes: int = 0
    tool_failures: int = 0
    tool_timeouts: int = 0
    safety_blocks: int = 0
    redactions: int = 0
    audio_frames_spoken: int = 0
    audio_frames_cancelled: int = 0
    latency: LatencyTracker = field(default_factory=LatencyTracker)

    def summary(self) -> dict[str, object]:
        lat = self.latency
        return {
            "turns": self.turns,
            "interruptions": self.interruptions,
            "tool_calls": self.tool_calls,
            "tool_successes": self.tool_successes,
            "tool_failures": self.tool_failures,
            "tool_timeouts": self.tool_timeouts,
            "safety_blocks": self.safety_blocks,
            "redactions": self.redactions,
            "audio_frames_spoken": self.audio_frames_spoken,
            "audio_frames_cancelled": self.audio_frames_cancelled,
            "avg_first_audio_ms": LatencyTracker._avg(lat.first_audio_ms),
            "avg_end_of_turn_ms": LatencyTracker._avg(lat.end_of_turn_ms),
            "avg_interruption_ms": LatencyTracker._avg(lat.interruption_ms),
            "latency_breaches": [str(b) for b in lat.breaches],
        }
