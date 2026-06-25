"""Tool registry — detect all installed AI coding tools."""

from __future__ import annotations

from ai_helper.tools.base import ToolInfo
from ai_helper.tools.claude_code import ClaudeCodeDetector
from ai_helper.tools.cursor import CursorDetector
from ai_helper.tools.opencode import OpenCodeDetector

DETECTORS = [
    ClaudeCodeDetector(),
    OpenCodeDetector(),
    CursorDetector(),
]


def detect_tools() -> list[ToolInfo]:
    return [detector.detect() for detector in DETECTORS]


def get_tool(name: str) -> ToolInfo | None:
    name_lower = name.lower().replace(" ", "")
    for detector in DETECTORS:
        if detector.name.lower().replace(" ", "") == name_lower:
            return detector.detect()
    return None
