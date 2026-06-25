"""Claude Code detection."""

from __future__ import annotations

from pathlib import Path

from ai_helper.tools.base import ToolDetector, ToolInfo


class ClaudeCodeDetector(ToolDetector):
    name = "Claude Code"
    binary_name = "claude"

    def _get_version(self, binary_path: str) -> str | None:
        version = super()._get_version(binary_path)
        if version:
            for line in version.splitlines():
                stripped = line.strip()
                if stripped and stripped[0].isdigit():
                    return stripped
                if "Claude Code" in stripped:
                    return stripped
        return version

    def _find_config(self) -> Path | None:
        path = Path.home() / ".claude" / "settings.json"
        if path.exists():
            return path
        return None

    def _find_sessions(self) -> Path | None:
        path = Path.home() / ".claude" / "projects"
        if path.exists():
            return path
        return None

    def _extract_model(self, config: dict) -> str | None:
        return config.get("model")

    def _extract_mcp_servers(self, config: dict) -> list[str]:
        servers = config.get("mcpServers", {})
        return list(servers.keys())

    def _check_issues(self, info: ToolInfo) -> None:
        if not info.config_path:
            info.issues.append("No global settings.json found at ~/.claude/settings.json")

        project_config = Path.cwd() / ".claude" / "settings.json"
        if project_config.exists():
            info.extras["project_config"] = str(project_config)

        agents_md = Path.cwd() / "CLAUDE.md"
        if not agents_md.exists():
            agents_md = Path.cwd() / "AGENTS.md"
        if agents_md.exists():
            info.extras["context_file"] = str(agents_md)
        else:
            info.issues.append("No CLAUDE.md or AGENTS.md in project root")

        rtk_hooks = info.config.get("hooks", {})
        has_rtk = any("rtk" in str(v).lower() for v in _flatten_values(rtk_hooks))
        info.extras["rtk_active"] = has_rtk


def _flatten_values(obj, depth=0):
    if depth > 5:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_values(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            yield from _flatten_values(item, depth + 1)
    else:
        yield obj
