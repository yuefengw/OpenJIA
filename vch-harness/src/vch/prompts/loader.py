"""Prompt loading helpers."""

from pathlib import Path


PROMPT_DIR = Path(__file__).parent


def load_role_prompt(name: str) -> str:
    """Load common protocol plus a role prompt."""
    common = _read_prompt("common_protocol.md")
    role = _read_prompt(name)
    return "\n\n".join(part for part in (common, role) if part.strip())


def _read_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()
