"""Base class for AI tool detection."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolInfo:
    """Detected information about an AI coding tool."""

    name: str
    installed: bool = False
    binary_path: str | None = None
    version: str | None = None
    config_path: Path | None = None
    config: dict = field(default_factory=dict)
    session_path: Path | None = None
    model: str | None = None
    mcp_servers: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    extras: dict = field(default_factory=dict)


class ToolDetector:
    """Base class for detecting an AI coding tool."""

    name: str = "unknown"
    binary_name: str = "unknown"

    def detect(self) -> ToolInfo:
        info = ToolInfo(name=self.name)
        info.binary_path = self._find_binary()
        info.installed = info.binary_path is not None

        if not info.installed:
            return info

        info.version = self._get_version(info.binary_path)
        info.config_path = self._find_config()

        if info.config_path and info.config_path.exists():
            info.config = self._read_config(info.config_path)
            info.model = self._extract_model(info.config)
            info.mcp_servers = self._extract_mcp_servers(info.config)

        info.session_path = self._find_sessions()
        self._check_issues(info)
        return info

    def _find_binary(self) -> str | None:
        return shutil.which(self.binary_name)

    def _get_version(self, binary_path: str) -> str | None:
        try:
            result = subprocess.run(
                [binary_path, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            pass
        return None

    def _find_config(self) -> Path | None:
        return None

    def _read_config(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _find_sessions(self) -> Path | None:
        return None

    def _extract_model(self, config: dict) -> str | None:
        return None

    def _extract_mcp_servers(self, config: dict) -> list[str]:
        return []

    def _check_issues(self, info: ToolInfo) -> None:
        pass
