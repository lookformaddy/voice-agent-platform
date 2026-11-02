"""Provider protocols and deterministic scripted providers.

No network, no API keys: the scripted providers exist so the state
machine, tools, safety screen and latency tracking can be exercised and
tested without any vendor. A real backend implements the same three
protocols and is swapped in at session construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Protocol


@dataclass(frozen=True)
class TranscriptChunk:
    text: str
    is_final: bool = False


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class AudioFrame:
    index: int
    text: str  # text segment this frame renders; a real TTS emits bytes


class ASRProvider(Protocol):
    def transcribe(self, audio_ref: str) -> Iterator[TranscriptChunk]: ...


class LLMProvider(Protocol):
    def respond(self, transcript: str, history: list[dict[str, str]]) -> LLMResponse: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str) -> Iterator[AudioFrame]: ...


class ScriptedASR:
    """Maps an audio reference to a fixed transcript, chunk by chunk."""

    def __init__(self, transcripts: dict[str, str] | None = None) -> None:
        self._transcripts = transcripts or {}

    def transcribe(self, audio_ref: str) -> Iterator[TranscriptChunk]:
        text = self._transcripts.get(audio_ref, audio_ref)
        words = text.split()
        for i, word in enumerate(words):
            yield TranscriptChunk(
                text=word + (" " if i < len(words) - 1 else ""),
                is_final=(i == len(words) - 1),
            )


class ScriptedLLM:
    """Keyword-driven replies. Deterministic: same transcript, same reply.

    Rules are (keyword, reply, tool_calls) triples, first match wins.
    The default rules exercise both scripted tools.
    """

    def __init__(
        self,
        rules: list[tuple[str, str, tuple[ToolCall, ...]]] | None = None,
    ) -> None:
        self._rules = rules if rules is not None else [
            (
                "hours",
                "Here are the hours I found for you.",
                (ToolCall("lookup", {"query": "store hours"}),),
            ),
            (
                "appointment",
                "Let me check availability for you.",
                (ToolCall("availability_check", {"slot": "next available"}),),
            ),
            (
                "long answer",
                "This is a deliberately long answer that keeps speaking "
                "across many audio frames so a barge-in can cut it short.",
                (),
            ),
        ]

    def respond(self, transcript: str, history: list[dict[str, str]]) -> LLMResponse:
        lowered = transcript.lower()
        for keyword, text, calls in self._rules:
            if keyword in lowered:
                return LLMResponse(text=text, tool_calls=calls)
        return LLMResponse(text="I heard you. How can I help next?")


class ScriptedTTS:
    """Splits text into one frame per sentence (or per ~40 chars)."""

    def synthesize(self, text: str) -> Iterator[AudioFrame]:
        parts = [p.strip() for p in text.replace(".", ".|").split("|") if p.strip()]
        if not parts:
            parts = [text]
        for i, part in enumerate(parts):
            yield AudioFrame(index=i, text=part)
