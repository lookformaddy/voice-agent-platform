"""Fail-closed safety screen, applied to agent text BEFORE speaking.

Two stages, in order:
1. Redact PII/secrets (email, phone, SSN-shaped, API-key-shaped) — the
   redacted text may still be spoken.
2. Block injection patterns (attempts to override instructions) — the
   turn is refused outright and nothing is spoken.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_API_KEY = re.compile(r"\b(?:api[_-]?key|secret|token)\s*[:=]\s*\S+", re.IGNORECASE)

_INJECTION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all )?(previous|prior|earlier) instructions",
        r"disregard (all )?(previous|prior) instructions",
        r"you are now ",
        r"new system prompt",
        r"override your instructions",
    )
]


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    text: str  # redacted text when allowed; refusal text when blocked
    redactions: tuple[str, ...] = ()
    blocked_reason: str = ""


class SafetyScreen:
    def screen(self, text: str) -> SafetyResult:
        for pattern in _INJECTION:
            if pattern.search(text):
                return SafetyResult(
                    allowed=False,
                    text="I can't comply with that request.",
                    blocked_reason=f"injection pattern matched: {pattern.pattern}",
                )
        redactions: list[str] = []
        screened = text
        for label, pattern in (
            ("email", _EMAIL),
            ("phone", _PHONE),
            ("ssn", _SSN),
            ("api_key", _API_KEY),
        ):
            if pattern.search(screened):
                redactions.append(label)
                screened = pattern.sub(f"[REDACTED {label.upper()}]", screened)
        return SafetyResult(allowed=True, text=screened, redactions=tuple(redactions))
