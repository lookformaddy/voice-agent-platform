from voice_agent import SessionConfig, VoiceSession
from voice_agent.config import InterruptionPolicy
from voice_agent.state import SessionState


def _speak_with_barge_in(session, after=1):
    spoken = []
    for frame in session.start_speech("One. Two. Three. Four."):
        spoken.append(frame.text)
        if len(spoken) == after:
            session.interrupt()
    return spoken


def test_barge_in_cancels_speech_and_returns_to_listening():
    session = VoiceSession()
    spoken = _speak_with_barge_in(session)
    assert spoken == ["One."]
    assert session.state == SessionState.LISTENING
    assert session.metrics.interruptions == 1
    assert session.metrics.audio_frames_cancelled == 3


def test_barge_in_when_not_speaking_is_noop():
    session = VoiceSession()
    assert session.interrupt() is False
    assert session.metrics.interruptions == 0


def test_ignore_policy_does_not_cancel():
    session = VoiceSession(
        SessionConfig(interruption_policy=InterruptionPolicy.IGNORE)
    )
    spoken = _speak_with_barge_in(session)
    assert spoken == ["One.", "Two.", "Three.", "Four."]
    assert session.metrics.interruptions == 0
    assert session.state == SessionState.LISTENING


def test_session_recovers_after_interruption():
    session = VoiceSession()
    _speak_with_barge_in(session)
    result = session.handle_turn("What are your store hours?")
    assert "9am to 6pm" in result.reply_text
    assert session.state == SessionState.LISTENING
