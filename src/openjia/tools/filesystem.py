"""Guarded filesystem write helpers."""

from pathlib import Path
import fnmatch


class GuardedFilesystem:
    """Write files only when they are allowed by the active contract."""

    def __init__(self, repo_root: str, allowed_paths: list[str]):
        self.repo_root = Path(repo_root).resolve()
        self.allowed_paths = [path.replace("\\", "/") for path in allowed_paths]

    def write_text(self, relative_path: str, content: str) -> Path:
        """Write text to an allowed repository-relative path."""
        normalized = relative_path.replace("\\", "/").lstrip("/")
        if not self.is_allowed(normalized):
            raise PermissionError(f"Path not allowed by contract: {normalized}")

        path = (self.repo_root / normalized).resolve()
        if not path.is_relative_to(self.repo_root):
            raise PermissionError(f"Path escapes repo root: {relative_path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def is_allowed(self, relative_path: str) -> bool:
        """Check whether a path matches allowed contract paths."""
        if not self.allowed_paths:
            return False
        normalized = relative_path.replace("\\", "/").lstrip("/")
        for pattern in self.allowed_paths:
            pattern = pattern.lstrip("/")
            if normalized == pattern or fnmatch.fnmatch(normalized, pattern):
                return True
        return False
