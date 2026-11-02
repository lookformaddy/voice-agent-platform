"""Optional FastAPI service layer. Stdlib core has no FastAPI dependency;
this module is only imported when the service is actually run.

Endpoints (JSON):
  POST /sessions                      -> {"session_id": ...}
  POST /sessions/{id}/turn           {"transcript": ...} -> TurnResult-ish
  POST /sessions/{id}/interrupt     -> {"interrupted": bool}
  GET  /sessions/{id}/metrics        -> metrics summary
"""

from __future__ import annotations

import uuid

from voice_agent.session import VoiceSession


def create_app():  # type: ignore[no-untyped-def]
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError as exc:  # pragma: no cover - exercised via skip test
        raise RuntimeError("FastAPI is required to run the service layer") from exc

    app = FastAPI(title="Voice Agent Platform")
    sessions: dict[str, VoiceSession] = {}

    class TurnRequest(BaseModel):
        transcript: str

    @app.post("/sessions")
    def create_session() -> dict[str, str]:
        session_id = str(uuid.uuid4())
        sessions[session_id] = VoiceSession()
        return {"session_id": session_id}

    def _get(session_id: str) -> VoiceSession:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="unknown session")
        return session

    @app.post("/sessions/{session_id}/turn")
    def turn(session_id: str, req: TurnRequest) -> dict[str, object]:
        result = _get(session_id).handle_turn(req.transcript)
        return {
            "reply_text": result.reply_text,
            "frames": list(result.frames),
            "blocked": result.blocked,
            "tool_results": [
                {"name": r.name, "ok": r.ok, "output": r.output, "error": r.error}
                for r in result.tool_results
            ],
        }

    @app.post("/sessions/{session_id}/interrupt")
    def interrupt(session_id: str) -> dict[str, bool]:
        return {"interrupted": _get(session_id).interrupt()}

    @app.get("/sessions/{session_id}/metrics")
    def metrics(session_id: str) -> dict[str, object]:
        return _get(session_id).metrics_summary()

    return app
