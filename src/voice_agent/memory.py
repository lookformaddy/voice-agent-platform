"""Short rolling conversation memory under a token/turn budget.

Token estimate is deliberately crude (chars / 4, rounded up) and
documented as such: it is a budget guard, not a tokenizer. Oldest turns
are evicted first until the turn fits both budgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    text: str


@dataclass
class RollingMemory:
    max_turns: int = 10
    max_tokens: int = 2000
    turns: list[Turn] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        return sum(estimate_tokens(t.text) for t in self.turns)

    def add(self, role: str, text: str) -> None:
        self.turns.append(Turn(role=role, text=text))
        while len(self.turns) > self.max_turns or (
            self.token_count > self.max_tokens and len(self.turns) > 1
        ):
            self.turns.pop(0)

    def as_history(self) -> list[dict[str, str]]:
        return [{"role": t.role, "text": t.text} for t in self.turns]
