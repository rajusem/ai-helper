"""Cursor detection."""

from __future__ import annotations

import platform
from pathlib import Path

from ai_helper.tools.base import ToolDetector, ToolInfo


class CursorDetector(ToolDetector):
    name = "Cursor"
    binary_name = "cursor"

    def _get_version(self, binary_path: str) -> str | None:
        version = super()._get_version(binary_path)
        if version:
            return version.splitlines()[0].strip()
        return version

    def _find_config(self) -> Path | None:
        system = platform.system()
        if system == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "Cursor"
            path = base / "User" / "settings.json"
        elif system == "Linux":
            path = Path.home() / ".config" / "Cursor" / "User" / "settings.json"
        else:
            path = Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "settings.json"

        if path.exists():
            return path
        return None

    def _find_mcp_config(self) -> Path | None:
        candidates = [
            Path.home() / ".cursor" / "mcp.json",
            Path.cwd() / ".cursor" / "mcp.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def detect(self) -> ToolInfo:
        info = super().detect()

        if info.installed:
            mcp_path = self._find_mcp_config()
            if mcp_path:
                mcp_config = self._read_config(mcp_path)
                info.mcp_servers = self._extract_mcp_servers(mcp_config)
                info.extras["mcp_config_path"] = str(mcp_path)

        app_installed = self._check_app_installed()
        if app_installed and not info.installed:
            info.installed = True
            info.extras["app_only"] = True
            info.issues.append("Cursor app found but 'cursor' CLI not in PATH")

        return info

    def _check_app_installed(self) -> bool:
        # macOS only — Linux/Windows detection not yet implemented
        if platform.system() == "Darwin":
            return Path("/Applications/Cursor.app").exists()
        return False

    def _find_sessions(self) -> Path | None:
        system = platform.system()
        if system == "Darwin":
            path = Path.home() / "Library" / "Application Support" / "Cursor"
        elif system == "Linux":
            path = Path.home() / ".config" / "Cursor"
        else:
            path = Path.home() / "AppData" / "Roaming" / "Cursor"

        if path.exists():
            return path
        return None

    def _extract_model(self, config: dict) -> str | None:
        return config.get("cursor.general.defaultModel")

    def _extract_mcp_servers(self, config: dict) -> list[str]:
        servers = config.get("mcpServers", {})
        return list(servers.keys())

    def _check_issues(self, info: ToolInfo) -> None:
        cursor_rules = Path.cwd() / ".cursorrules"
        cursor_dir = Path.cwd() / ".cursor" / "rules"
        if cursor_rules.exists():
            info.extras["rules_file"] = str(cursor_rules)
        elif cursor_dir.exists():
            info.extras["rules_dir"] = str(cursor_dir)
