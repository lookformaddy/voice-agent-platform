# Voice Agent Platform

> AI Engineering track · clean-room, fully original code · synthetic data only

An enterprise-grade realtime voice-agent session engine: a validated
state machine, streaming transcripts, pluggable ASR/TTS/LLM providers,
tool calls inside a voice turn, latency budgets, rolling conversation
memory, and a fail-closed safety screen — with an optional FastAPI
service layer on top of a stdlib-only core.

## The enterprise problem

Voice agents fail in production not on the happy path but on the edges:
a user barges in while the agent is speaking, a tool hangs, a latency
budget silently blows, or unsafe text reaches the speaker. This project
models those edges explicitly: every one of them has a state, a metric,
and a test — so an interruption is a first-class transition, a tool
timeout is a recorded result, and a budget breach is a flagged metric,
never a silent drop or a hung session.

## Architecture overview

See [`docs/architecture.md`](docs/architecture.md) for the full design.

```
User audio ──► ScriptedASR (streaming chunks) ──► VoiceSession (state machine)
                                                            │ LISTENING → THINKING
                                                            ▼ → SPEAKING → LISTENING
                                              ScriptedLLM ──► ToolRegistry (lookup,
                                              availability_check; timeout/failure
                                              as results, never crashes)
                                                            ▼
                                              SafetyScreen (PII/secret redaction,
                                              injection-pattern block) ──► ScriptedTTS
                                              (frame stream, cancellable mid-speech)
```

Core modules (`src/voice_agent/`): `state.py` (validated transitions),
`session.py` (one conversation, owns the state machine), `providers.py`
(protocols + deterministic scripted providers), `tools.py`, `safety.py`,
`memory.py` (rolling memory under token/turn budgets), `latency.py`
(budget tracking + breach records), `metrics.py`, `config.py`,
`service.py` (optional FastAPI layer — stdlib core has no FastAPI dep).

## How to run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # pytest only; FastAPI optional
python demo.py                    # scripted conversation incl. one barge-in
pytest                            # full suite (service test auto-skips w/o FastAPI)
make test                         # same, via Makefile
make demo
```

Optional service (requires FastAPI + uvicorn):

```bash
pip install fastapi uvicorn
python -m uvicorn voice_agent.service:create_app --factory --port 8000
# or: PYTHONPATH=src python -c "from voice_agent.service import create_app"
```

## Key design decisions and trade-offs

- **State machine, not flags.** Transitions are validated centrally
  (`state.py`), so an impossible move raises instead of corrupting a
  session. `INTERRUPTED` is transient: the session returns to
  `LISTENING` as soon as synthesis is cancelled.
- **Scripted providers, real seams.** No network, no API keys. The
  ASR/TTS/LLM protocols are the integration points; a vendor backend
  implements the same three protocols and swaps in at construction.
  Determinism is a feature here: demos and tests are reproducible.
- **Tools run in a worker thread with a timeout.** A slow tool becomes
  a `timed_out` result counted in metrics, not a hung turn. Tool
  failures likewise surface as results, never exceptions to the caller.
- **Fail-closed safety, in order.** Redaction first (PII/secrets may
  still be spoken, redacted), injection block second (nothing spoken).
  The screen runs on composed text *after* tool outputs are merged in,
  so a tool cannot smuggle unsafe text past it.
- **Crude token estimate, honestly labelled.** Memory uses chars/4 as
  a budget guard, not a tokenizer — documented in `memory.py`. Swap in
  a real tokenizer when a vendor LLM is plugged in.
- **Latency measured, not simulated.** Turn timing uses wall-clock
  monotonic time; breaches append to `latency.breaches` and appear in
  the metrics summary. Budgets are per-session config, not globals.

## CI

The CI definition lives at `docs/github-actions-ci.yml` (not
`.github/workflows/`, because the GitHub App used to push this repo
lacks the Workflows permission). It activates by moving that file to
`.github/workflows/ci.yml` — it runs `pytest` on Python 3.12.

## What it demonstrates

Realtime session design (state machine + barge-in), provider
abstraction for vendor swap-out, tool orchestration with timeout and
failure semantics, safety-before-speech, latency-budget observability,
and bounded conversation memory — the building blocks of a production
voice agent, exercised end to end without any vendor dependency.

## Project links

Repository: [lookformaddy/voice-agent-platform](https://github.com/lookformaddy/voice-agent-platform)
