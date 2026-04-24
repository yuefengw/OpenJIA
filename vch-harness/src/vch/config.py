"""VCH Config module."""

from pathlib import Path
from typing import Optional
import json


class Config:
    """VCH Configuration."""

    DEFAULT_MAX_SPRINTS = 3
    DEFAULT_MAX_REPAIR_ATTEMPTS = 3
    DEFAULT_MAX_FILES_PER_SPRINT = 8

    def __init__(
        self,
        repo_root: Optional[str] = None,
        max_sprints: int = DEFAULT_MAX_SPRINTS,
        max_repair_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS,
        max_files_per_sprint: int = DEFAULT_MAX_FILES_PER_SPRINT,
        llm_backend: str = "deterministic",
        llm_model: str = "gpt-4.1",
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.max_sprints = max_sprints
        self.max_repair_attempts = max_repair_attempts
        self.max_files_per_sprint = max_files_per_sprint
        self.llm_backend = llm_backend
        self.llm_model = llm_model

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load config from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(
            repo_root=data.get("repo_root"),
            max_sprints=data.get("max_sprints", cls.DEFAULT_MAX_SPRINTS),
            max_repair_attempts=data.get("max_repair_attempts", cls.DEFAULT_MAX_REPAIR_ATTEMPTS),
            max_files_per_sprint=data.get("max_files_per_sprint", cls.DEFAULT_MAX_FILES_PER_SPRINT),
            llm_backend=data.get("llm_backend", "deterministic"),
            llm_model=data.get("llm_model", "gpt-4.1"),
        )

    def to_file(self, path: str) -> None:
        """Save config to a JSON file."""
        data = {
            "repo_root": str(self.repo_root),
            "max_sprints": self.max_sprints,
            "max_repair_attempts": self.max_repair_attempts,
            "max_files_per_sprint": self.max_files_per_sprint,
            "llm_backend": self.llm_backend,
            "llm_model": self.llm_model,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
