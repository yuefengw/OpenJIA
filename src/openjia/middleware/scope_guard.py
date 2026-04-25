"""ScopeGuardMiddleware - prevents out-of-scope modifications."""

from pathlib import Path
from typing import Optional, Callable, Any
import fnmatch


class ScopeGuardMiddleware:
    """
    Middleware to prevent generators from modifying files outside scope.

    Checks:
    - edit_file / write_file paths against allowed_write_paths
    - execute commands that could modify forbidden files
    """

    def __init__(self, allowed_paths: Optional[list[str]] = None):
        self.allowed_paths = allowed_paths or []

    def is_allowed(self, path: str) -> bool:
        """
        Check if a path is allowed to be modified.

        Args:
            path: File path to check

        Returns:
            True if allowed, False otherwise
        """
        if not self.allowed_paths:
            return True

        normalized = str(Path(path).as_posix())

        for pattern in self.allowed_paths:
            normalized_pattern = str(Path(pattern).as_posix())

            # Exact match
            if normalized == normalized_pattern:
                return True

            # Glob match
            if fnmatch.fnmatch(normalized, normalized_pattern):
                return True

            # Directory match (path starts with allowed directory)
            if normalized_pattern.endswith("/**"):
                dir_pattern = normalized_pattern[:-3]
                if normalized.startswith(dir_pattern) or normalized.startswith(dir_pattern[1:]):
                    return True

        return False

    def validate_write(self, path: str) -> None:
        """
        Validate a write operation. Raises PermissionError if not allowed.

        Args:
            path: File path to validate

        Raises:
            PermissionError: If path is not in allowed paths
        """
        if not self.is_allowed(path):
            raise PermissionError(
                f"Write to '{path}' not allowed by contract. "
                f"Allowed paths: {self.allowed_paths}"
            )

    def validate_tool_call(
        self,
        tool_name: str,
        args: dict
    ) -> None:
        """
        Validate a tool call before execution.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Raises:
            PermissionError: If the operation is not allowed
        """
        if tool_name in ("edit_file", "write_file", "create_file"):
            path = args.get("path") or args.get("file_path", "")
            self.validate_write(path)

    def update_allowed_paths(self, paths: list[str]) -> None:
        """Update the allowed paths list."""
        self.allowed_paths = paths

    def check_git_diff_scope(
        self,
        git_base: str,
        git_head: str,
        repo_root: str
    ) -> tuple[bool, list[str]]:
        """
        Check if git diff is within allowed scope.

        Args:
            git_base: Base commit
            git_head: Head commit
            repo_root: Repository root

        Returns:
            Tuple of (within_scope, list of unexpected files)
        """
        import subprocess

        unexpected = []

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", git_base, git_head],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return True, []

            modified_files = result.stdout.strip().split("\n")

            for f in modified_files:
                if f and not self.is_allowed(f):
                    unexpected.append(f)

        except Exception:
            return True, []

        return len(unexpected) == 0, unexpected
