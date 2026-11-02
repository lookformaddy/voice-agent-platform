from voice_agent import VoiceSession
from voice_agent.tools import Tool, ToolRegistry


def test_lookup_tool_turn():
    session = VoiceSession()
    result = session.handle_turn("What are your store hours?")
    assert len(result.tool_results) == 1
    assert result.tool_results[0].ok
    assert "9am to 6pm" in result.tool_results[0].output
    assert session.metrics.tool_successes == 1


def test_availability_tool_turn():
    session = VoiceSession()
    result = session.handle_turn("Can I book an appointment?")
    assert result.tool_results[0].name == "availability_check"
    assert "Tuesday 10:00" in result.tool_results[0].output


def test_unknown_tool_is_failure_not_crash():
    registry = ToolRegistry()
    result = registry.call("nope", {}, timeout_seconds=1.0)
    assert not result.ok and "unknown tool" in result.error


def test_failing_tool_is_failure_not_crash():
    def boom(_args):
        raise RuntimeError("synthetic failure")

    registry = ToolRegistry([Tool("boom", boom)])
    result = registry.call("boom", {}, timeout_seconds=1.0)
    assert not result.ok and "RuntimeError" in result.error


def test_slow_tool_times_out():
    registry = ToolRegistry([Tool("slow", lambda _a: "late", delay_seconds=2.0)])
    result = registry.call("slow", {}, timeout_seconds=0.1)
    assert not result.ok and result.timed_out
