import pytest

from voice_agent.session import VoiceSession
from voice_agent.state import SessionState, transition


def test_legal_and_illegal_transitions():
    assert transition(SessionState.LISTENING, SessionState.THINKING) == SessionState.THINKING
    with pytest.raises(ValueError):
        transition(SessionState.THINKING, SessionState.THINKING)


def test_full_turn_returns_to_listening():
    session = VoiceSession()
    result = session.handle_turn("Hello there")
    assert session.state == SessionState.LISTENING
    assert result.reply_text
    assert session.metrics.turns == 1


def test_streaming_transcript_chunks():
    session = VoiceSession()
    chunks = list(session.transcribe("hello world"))
    assert "".join(c.text for c in chunks) == "hello world"
    assert chunks[-1].is_final
    assert not chunks[0].is_final
