"""Scripted tools with timeout and failure handling.

Tools run in a worker thread so a slow or hanging tool cannot block the
voice turn past ``timeout_seconds``; a timeout is recorded as a failed
tool result, never as a silent drop or a hung session.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
import time
from typing import Callable


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    output: str = ""
    error: str = ""
    timed_out: bool = False


@dataclass
class Tool:
    name: str
    func: Callable[[dict[str, str]], str]
    description: str = ""
    # Simulated latency (seconds) for scripted tools; real tools use 0.
    delay_seconds: float = 0.0

    def run(self, arguments: dict[str, str]) -> str:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        return self.func(arguments)


def lookup_tool(arguments: dict[str, str]) -> str:
    """Scripted knowledge lookup over a tiny synthetic catalogue."""
    catalogue = {
        "store hours": "Open Monday to Saturday, 9am to 6pm.",
        "returns": "Returns are accepted within 30 days with a receipt.",
    }
    return catalogue.get(
        arguments.get("query", ""), "No entry found for that query."
    )


def availability_check_tool(arguments: dict[str, str]) -> str:
    """Scripted scheduling-style availability check (synthetic slots)."""
    return f"Next available slot for '{arguments.get('slot', 'any')}' is Tuesday 10:00."


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools = {t.name: t for t in (tools or self.default_tools())}

    @staticmethod
    def default_tools() -> list[Tool]:
        return [
            Tool("lookup", lookup_tool, "Look up a fact in the catalogue."),
            Tool(
                "availability_check",
                availability_check_tool,
                "Check availability for a scheduling-style request.",
            ),
        ]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def call(
        self, name: str, arguments: dict[str, str], timeout_seconds: float
    ) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name=name, ok=False, error=f"unknown tool: {name}")
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(tool.run, arguments)
                output = future.result(timeout=timeout_seconds)
            return ToolResult(name=name, ok=True, output=output)
        except FutureTimeout:
            return ToolResult(
                name=name, ok=False, error="tool timed out", timed_out=True
            )
        except Exception as exc:  # tool failure is a result, not a crash
            return ToolResult(name=name, ok=False, error=f"{type(exc).__name__}: {exc}")
