# Architecture

## Components

```
┌──────────┐   chunks   ┌──────────────┐   reply+tools  ┌──────────────┐
│ Scripted │ ─────────► │ VoiceSession │ ─────────────► │ ToolRegistry │
│ ASR      │            │ (state       │                │ lookup,      │
└──────────┘            │  machine)    │ ◄───────────── │ availability │
                        │              │   results      │ _check       │
                        │  THINKING    │                └──────────────┘
                        │      │       │
                        │      ▼       │  screened text
                        │ SafetyScreen │ ─────────► ┌──────────────┐
                        │ (redact,     │            │ ScriptedTTS  │
                        │  block)      │            │ frame stream │
                        │      │       │            │ (cancellable)│
                        │      ▼       │            └──────────────┘
                        │  SPEAKING ───┼── interrupt() ──► INTERRUPTED
                        │      │       │                    │
                        │      ▼       │                    ▼
                        │  LISTENING ◄─┴────────────────────┘
                        └──────┬───────┘
                               │ turns, latencies, breaches
                               ▼
                        SessionMetrics + RollingMemory
```

## State machine

| From | Legal next states |
|---|---|
| LISTENING | THINKING, SPEAKING, INTERRUPTED |
| THINKING | SPEAKING, LISTENING, INTERRUPTED |
| SPEAKING | LISTENING, INTERRUPTED |
| INTERRUPTED | LISTENING |

Illegal transitions raise `ValueError` from `state.transition`.

## Turn pipeline (in order)

1. Transcript arrives; session moves LISTENING → THINKING; user turn
   appended to rolling memory.
2. LLM responds (scripted, keyword-driven) with optional tool calls.
3. Each tool runs in a worker thread under the session timeout;
   success / failure / timeout are all recorded results, and tool
   output is merged into the reply text.
4. Safety screen runs on the composed text: redact PII/secrets, or
   block the turn entirely on an injection pattern (nothing spoken,
   refusal stored in memory instead).
5. TTS frames stream (THINKING → SPEAKING). `interrupt()` under the
   `allow` policy flags cancellation; the generator stops at the next
   frame boundary, counts the remaining frames cancelled, records
   interruption latency, and returns via INTERRUPTED → LISTENING.
   Under the `ignore` policy the interruption is a no-op.
6. End-of-turn latency and first-audio latency are recorded against
   the session budgets; breaches are appended, never dropped.

## Memory and budgets

`RollingMemory` evicts oldest turns first until both the turn cap and
the token cap (chars/4 estimate) hold. `LatencyTracker` keeps per-turn
measurements and a breach list surfaced in `SessionMetrics.summary()`.

## Extension points

- Real ASR/TTS/LLM: implement the three protocols in `providers.py`
  and pass instances to `VoiceSession(...)`.
- Real tools: register `Tool` objects with `ToolRegistry`; keep the
  timeout semantics — a voice turn must never hang on a tool.
- Real tokenizer: replace `memory.estimate_tokens` when a vendor LLM
  is plugged in; the budget interface is unchanged.
- Service: `voice_agent.service.create_app()` wraps sessions behind
  FastAPI; the stdlib core stays dependency-free.
