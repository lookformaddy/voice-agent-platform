"""Scripted demo: two tool-using turns, then a barge-in mid-speech.

Run:  python demo.py        (no network, no API keys)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from voice_agent import VoiceSession  # noqa: E402


def main() -> None:
    session = VoiceSession()
    print("== Turn 1: tool call (lookup) ==")
    result = session.handle_turn("What are your store hours?")
    print(f"Agent: {result.reply_text}")
    print(f"Frames spoken: {len(result.frames)} | state: {session.state.value}")

    print("\n== Turn 2: tool call (availability check) ==")
    result = session.handle_turn("Can I book an appointment?")
    print(f"Agent: {result.reply_text}")
    print(f"Frames spoken: {len(result.frames)} | state: {session.state.value}")

    print("\n== Turn 3: barge-in ==")
    print("Agent starts a long answer; user interrupts after the first frame.")
    spoken = []
    for frame in session.start_speech(
        "This is a deliberately long answer. It keeps going. "
        "And going. And it would keep going without interruption."
    ):
        spoken.append(frame.text)
        print(f"  [audio frame] {frame.text}")
        if len(spoken) == 1:
            interrupted = session.interrupt()
            print(f"  User barges in -> interrupt() returned {interrupted}")
    print(f"Frames before interruption: {len(spoken)} | state: {session.state.value}")
    assert session.state.value == "listening", "session must return to listening"

    print("\n== Turn 4: conversation resumes after interruption ==")
    result = session.handle_turn("Thanks, that's all I needed.")
    print(f"Agent: {result.reply_text}")

    print("\n== Session metrics ==")
    print(json.dumps(session.metrics_summary(), indent=2))
    print("\nDemo OK: barge-in cancelled speech and the session recovered.")


if __name__ == "__main__":
    main()
