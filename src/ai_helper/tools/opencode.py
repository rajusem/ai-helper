"""OpenCode detection."""

from __future__ import annotations

from pathlib import Path

from ai_helper.tools.base import ToolDetector, ToolInfo


class OpenCodeDetector(ToolDetector):
    name = "OpenCode"
    binary_name = "opencode"

    def _find_binary(self) -> str | None:
        path = super()._find_binary()
        if path:
            return path
        known_paths = [
            Path.home() / ".opencode" / "bin" / "opencode",
            Path("/opt/homebrew/bin/opencode"),
            Path("/usr/local/bin/opencode"),
        ]
        for p in known_paths:
            if p.exists():
                return str(p)
        return None

    def _find_config(self) -> Path | None:
        candidates = [
            Path.home() / ".config" / "opencode" / "opencode.json",
            Path.home() / ".config" / "opencode" / "config.toml",
            Path.home() / ".opencode" / "config.toml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _read_config(self, path: Path) -> dict:
        if path.suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore[no-redefine]
                except ImportError:
                    return {}
            try:
                return tomllib.loads(path.read_text())
            except Exception:
                return {}
        return super()._read_config(path)

    def _find_sessions(self) -> Path | None:
        candidates = [
            Path.home() / ".config" / "opencode" / "sessions",
            Path.home() / ".opencode" / "sessions",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _extract_model(self, config: dict) -> str | None:
        model = config.get("model") or config.get("default", {}).get("model")
        if model:
            return model
        return None

    def _extract_small_model(self, config: dict) -> str | None:
        return config.get("small_model")

    def _extract_mcp_servers(self, config: dict) -> list[str]:
        servers = config.get("mcpServers", config.get("mcp", {}).get("servers", {}))
        if isinstance(servers, dict):
            return list(servers.keys())
        return []

    def _check_issues(self, info: ToolInfo) -> None:
        small_model = self._extract_small_model(info.config)
        if small_model:
            info.extras["small_model"] = small_model

        project_config = Path.cwd() / ".opencode"
        if project_config.exists():
            info.extras["project_config"] = str(project_config)

            agents_dir = project_config / "agents"
            if agents_dir.exists():
                agents = [f.stem for f in agents_dir.glob("*.md")]
                info.extras["agents"] = agents

            skills_dir = project_config / "skills"
            if skills_dir.exists():
                skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
                info.extras["skills"] = skills
