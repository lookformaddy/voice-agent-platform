"""Voice Agent Platform: realtime voice-agent sessions, clean-room demo.

Public surface: session state machine, scripted providers, tools,
safety screening, latency budgets, rolling memory and metrics.
All providers in this package are deterministic and offline; real
ASR/TTS/LLM backends plug in behind the same protocols.
"""

from voice_agent.config import InterruptionPolicy, LatencyBudgets, SessionConfig
from voice_agent.latency import LatencyTracker
from voice_agent.memory import RollingMemory
from voice_agent.metrics import SessionMetrics
from voice_agent.providers import (
    LLMResponse,
    ScriptedASR,
    ScriptedLLM,
    ScriptedTTS,
    ToolCall,
    TranscriptChunk,
)
from voice_agent.safety import SafetyResult, SafetyScreen
from voice_agent.session import TurnResult, VoiceSession
from voice_agent.state import SessionState
from voice_agent.tools import Tool, ToolRegistry, ToolResult

__all__ = [
    "InterruptionPolicy",
    "LatencyBudgets",
    "LatencyTracker",
    "LLMResponse",
    "RollingMemory",
    "SafetyResult",
    "SafetyScreen",
    "ScriptedASR",
    "ScriptedLLM",
    "ScriptedTTS",
    "SessionConfig",
    "SessionMetrics",
    "SessionState",
    "Tool",
    "ToolCall",
    "ToolRegistry",
    "ToolResult",
    "TranscriptChunk",
    "TurnResult",
    "VoiceSession",
]

__version__ = "0.1.0"
