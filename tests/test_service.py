import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from voice_agent.service import create_app  # noqa: E402


def test_service_turn_and_metrics():
    client = TestClient(create_app())
    session_id = client.post("/sessions").json()["session_id"]
    turn = client.post(
        f"/sessions/{session_id}/turn", json={"transcript": "store hours please"}
    ).json()
    assert "9am to 6pm" in turn["reply_text"]
    metrics = client.get(f"/sessions/{session_id}/metrics").json()
    assert metrics["turns"] == 1
    assert metrics["tool_successes"] == 1
    assert client.post(f"/sessions/{session_id}/interrupt").json() == {
        "interrupted": False
    }
