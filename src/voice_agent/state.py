"""Session state machine. Transitions are validated centrally so no caller
can move a session into an impossible state (e.g. THINKING -> THINKING)."""

from __future__ import annotations

from enum import Enum


class SessionState(str, Enum):
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


# Legal transitions. INTERRUPTED is transient: the session returns to
# LISTENING as soon as in-flight synthesis is cancelled (see session.py).
_ALLOWED: dict[SessionState, frozenset[SessionState]] = {
    SessionState.LISTENING: frozenset(
        {SessionState.THINKING, SessionState.SPEAKING, SessionState.INTERRUPTED}
    ),
    SessionState.THINKING: frozenset(
        {SessionState.SPEAKING, SessionState.LISTENING, SessionState.INTERRUPTED}
    ),
    SessionState.SPEAKING: frozenset(
        {SessionState.LISTENING, SessionState.INTERRUPTED}
    ),
    SessionState.INTERRUPTED: frozenset({SessionState.LISTENING}),
}


def can_transition(from_state: SessionState, to_state: SessionState) -> bool:
    return to_state in _ALLOWED[from_state]


def transition(from_state: SessionState, to_state: SessionState) -> SessionState:
    """Return ``to_state`` or raise ValueError for an illegal transition."""
    if not can_transition(from_state, to_state):
        raise ValueError(f"illegal transition {from_state.value} -> {to_state.value}")
    return to_state
