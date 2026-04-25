"""ContextManifestMiddleware - injects context boundaries into agent calls."""

from pathlib import Path
from typing import Optional
import yaml

from openjia.context.manifest import ContextManifest


class ContextManifestMiddleware:
    """
    Middleware that ensures agents read context manifest before starting.

    Rules enforced:
    - CONTRACT.yaml must be read first
    - CONTEXT_MANIFEST.yaml must be read first
    - Manifest澶?files cannot be read directly
    - Write paths must be in allowed_write_paths
    """

    def __init__(self, manifest: Optional[ContextManifest] = None):
        self.manifest = manifest

    def set_manifest(self, manifest: ContextManifest) -> None:
        """Set the context manifest."""
        self.manifest = manifest

    def validate_read(self, file_path: str) -> None:
        """
        Validate a read operation against the manifest.

        Args:
            file_path: Path being read

        Raises:
            PermissionError: If the file is in forbidden context
        """
        if not self.manifest:
            return

        normalized = str(Path(file_path).as_posix())

        # Check forbidden context
        for forbidden in self.manifest.forbidden_context:
            if forbidden.lower() in normalized.lower():
                raise PermissionError(
                    f"Reading '{file_path}' not allowed. "
                    f"Context '{forbidden}' is forbidden."
                )

    def validate_write(self, file_path: str) -> None:
        """
        Validate a write operation against the manifest.

        Args:
            file_path: Path being written

        Raises:
            PermissionError: If the path is not in allowed_write_paths
        """
        if not self.manifest:
            return

        normalized = str(Path(file_path).as_posix())

        if not self.allowed_to_write(normalized):
            raise PermissionError(
                f"Writing to '{file_path}' not allowed by manifest. "
                f"Allowed paths: {self.manifest.allowed_write_paths}"
            )

    def allowed_to_write(self, file_path: str) -> bool:
        """Check if a path is allowed to write."""
        if not self.manifest:
            return True

        for pattern in self.manifest.allowed_write_paths:
            if self._match_path(file_path, pattern):
                return True

        return False

    def allowed_to_read(self, file_path: str) -> bool:
        """Check if a path is allowed to read."""
        if not self.manifest:
            return True

        normalized = str(Path(file_path).as_posix())

        # Check must_read
        for path in self.manifest.get_all_must_read():
            if self._match_path(normalized, path):
                return True

        # Check may_read
        for path in self.manifest.get_all_may_read():
            if self._match_path(normalized, path):
                return True

        return False

    def _match_path(self, path: str, pattern: str) -> bool:
        """Match a path against a pattern."""
        import fnmatch

        normalized_path = path.replace("\\", "/")
        normalized_pattern = pattern.replace("\\", "/")

        # Exact match
        if normalized_path == normalized_pattern:
            return True

        # Glob match
        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            return True

        # Directory pattern
        if normalized_pattern.endswith("/**"):
            dir_part = normalized_pattern[:-3]
            if normalized_path.startswith(dir_part):
                return True

        return False

    def get_context_summary(self) -> str:
        """
        Get a human-readable summary of the current context.

        Returns:
            Summary string
        """
        if not self.manifest:
            return "No manifest set"

        lines = [
            f"Sprint: {self.manifest.sprint_id}",
            f"Git: {self.manifest.git_base[:8]}... -> {self.manifest.git_head[:8]}...",
            "",
            "Must Read:",
        ]

        for path in self.manifest.get_all_must_read():
            lines.append(f"  - {path}")

        if self.manifest.get_all_may_read():
            lines.append("")
            lines.append("May Read:")
            for path in self.manifest.get_all_may_read()[:10]:
                lines.append(f"  - {path}")

        if self.manifest.latest_failure:
            lines.append("")
            lines.append("Latest Failure:")
            failed = self.manifest.latest_failure.get("failed_criteria", [])
            lines.append(f"  Failed ACs: {', '.join(failed)}")

        return "\n".join(lines)
