"""Voice session: owns the state machine for one conversation.

Flow for a normal turn::

    LISTENING --utterance--> THINKING --reply ready--> SPEAKING
    SPEAKING --frames done--> LISTENING

Barge-in while SPEAKING (policy ``allow``)::

    SPEAKING --interrupt()--> INTERRUPTED --> LISTENING

``handle_turn`` runs a complete turn. ``start_speech`` exposes the
speaking generator so a caller (or the demo) can interrupt mid-speech:
iterating it yields frames until synthesis finishes or ``interrupt()``
cancels it, at which point the remaining frames are counted cancelled
and the session is back in LISTENING.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Iterator

from voice_agent.config import InterruptionPolicy, SessionConfig
from voice_agent.latency import LatencyTracker
from voice_agent.memory import RollingMemory
from voice_agent.metrics import SessionMetrics
from voice_agent.providers import (
    AudioFrame,
    LLMProvider,
    ScriptedASR,
    ScriptedLLM,
    ScriptedTTS,
    TranscriptChunk,
)
from voice_agent.safety import SafetyResult, SafetyScreen
from voice_agent.state import SessionState, transition
from voice_agent.tools import ToolRegistry, ToolResult


@dataclass
class TurnResult:
    transcript: str
    reply_text: str
    tool_results: tuple[ToolResult, ...] = ()
    safety: SafetyResult | None = None
    frames: tuple[str, ...] = ()
    blocked: bool = False
    interrupted: bool = False


class VoiceSession:
    def __init__(
        self,
        config: SessionConfig | None = None,
        llm: LLMProvider | None = None,
        tts: ScriptedTTS | None = None,
        asr: ScriptedASR | None = None,
        tools: ToolRegistry | None = None,
        safety: SafetyScreen | None = None,
    ) -> None:
        self.config = config or SessionConfig()
        self.llm = llm or ScriptedLLM()
        self.tts = tts or ScriptedTTS()
        self.asr = asr or ScriptedASR()
        self.tools = tools or ToolRegistry()
        self.safety = safety or SafetyScreen()
        self.memory = RollingMemory(
            max_turns=self.config.max_memory_turns,
            max_tokens=self.config.max_memory_tokens,
        )
        self.metrics = SessionMetrics(latency=LatencyTracker(self.config.latency_budgets))
        self._state = SessionState.LISTENING
        self._speech_cancelled = False
        self._interrupt_started_ms: float | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    def _set_state(self, new: SessionState) -> None:
        self._state = transition(self._state, new)

    # -- ASR -----------------------------------------------------------
    def transcribe(self, audio_ref: str) -> Iterator[TranscriptChunk]:
        """Stream transcript chunks for an audio reference (LISTENING)."""
        yield from self.asr.transcribe(audio_ref)

    # -- Speech --------------------------------------------------------
    def start_speech(self, text: str) -> Iterator[AudioFrame]:
        """Yield TTS frames for ``text``; honours a mid-stream interrupt."""
        if self._state == SessionState.THINKING:
            self._set_state(SessionState.SPEAKING)
        elif self._state == SessionState.LISTENING:
            self._set_state(SessionState.SPEAKING)
        else:
            raise ValueError(f"cannot start speech while {self._state.value}")
        self._speech_cancelled = False
        frames = list(self.tts.synthesize(text))
        for frame in frames:
            if self._speech_cancelled:
                remaining = len(frames) - frame.index
                self.metrics.audio_frames_cancelled += remaining
                self._finish_interruption()
                return
            self.metrics.audio_frames_spoken += 1
            yield frame
        self._set_state(SessionState.LISTENING)

    def _finish_interruption(self) -> None:
        if self._interrupt_started_ms is not None:
            elapsed = time.monotonic() * 1000 - self._interrupt_started_ms
            self.metrics.latency.record_interruption(elapsed)
            self._interrupt_started_ms = None
        self._set_state(SessionState.INTERRUPTED)
        self._set_state(SessionState.LISTENING)

    def interrupt(self) -> bool:
        """Barge-in: cancel in-flight synthesis and return to listening.

        Returns True only when speech was actually cancelled. Under the
        ``ignore`` policy, or when not speaking, this is a no-op.
        """
        if self._state != SessionState.SPEAKING:
            return False
        if self.config.interruption_policy != InterruptionPolicy.ALLOW:
            return False
        self._interrupt_started_ms = time.monotonic() * 1000
        self._speech_cancelled = True
        self.metrics.interruptions += 1
        return True

    # -- Full turn -----------------------------------------------------
    def handle_turn(self, transcript: str) -> TurnResult:
        """Run one user utterance end to end: LLM, tools, safety, speech."""
        started_ms = time.monotonic() * 1000
        self._set_state(SessionState.THINKING)
        self.memory.add("user", transcript)
        response = self.llm.respond(transcript, self.memory.as_history())

        tool_results: list[ToolResult] = []
        reply = response.text
        for call in response.tool_calls:
            result = self.tools.call(
                call.name, call.arguments, self.config.tool_timeout_seconds
            )
            tool_results.append(result)
            self.metrics.tool_calls += 1
            if result.timed_out:
                self.metrics.tool_timeouts += 1
            elif result.ok:
                self.metrics.tool_successes += 1
            else:
                self.metrics.tool_failures += 1
            reply += f" [{result.name}: {result.output or result.error}]"

        screened = self.safety.screen(reply)
        self.metrics.redactions += len(screened.redactions)
        if not screened.allowed:
            self.metrics.safety_blocks += 1
            self.memory.add("assistant", screened.text)
            self.metrics.turns += 1
            self.metrics.latency.record_end_of_turn(time.monotonic() * 1000 - started_ms)
            self._set_state(SessionState.LISTENING)
            return TurnResult(
                transcript=transcript,
                reply_text=screened.text,
                tool_results=tuple(tool_results),
                safety=screened,
                blocked=True,
            )

        first_audio_ms: float | None = None
        spoken: list[str] = []
        for frame in self.start_speech(screened.text):
            if first_audio_ms is None:
                first_audio_ms = time.monotonic() * 1000 - started_ms
            spoken.append(frame.text)
        if first_audio_ms is not None:
            self.metrics.latency.record_first_audio(first_audio_ms)
        self.metrics.latency.record_end_of_turn(time.monotonic() * 1000 - started_ms)
        self.memory.add("assistant", screened.text)
        self.metrics.turns += 1
        return TurnResult(
            transcript=transcript,
            reply_text=screened.text,
            tool_results=tuple(tool_results),
            safety=screened,
            frames=tuple(spoken),
        )

    def metrics_summary(self) -> dict[str, object]:
        return self.metrics.summary()
