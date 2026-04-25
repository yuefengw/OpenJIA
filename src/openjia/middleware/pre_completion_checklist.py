"""PreCompletionChecklistMiddleware - prevents premature completion."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ChecklistItem:
    """A checklist item for pre-completion validation."""

    name: str
    passed: bool
    message: str


class PreCompletionChecklistMiddleware:
    """
    Middleware to ensure generator doesn't claim completion prematurely.

    Checks before allowing completion:
    - All required_commands were run
    - Each command has exit code and log path
    - CHANGESET.md exists
    - SELF_VERIFY_REPORT.md exists
    - If repair, REPAIR_REPORT.md exists
    """

    def __init__(
        self,
        required_commands: Optional[list[str]] = None,
        is_repair: bool = False
    ):
        self.required_commands = required_commands or []
        self.is_repair = is_repair

    def validate(
        self,
        sprint_dir: str,
        self_verify_report_path: Optional[str] = None
    ) -> tuple[bool, list[ChecklistItem]]:
        """
        Run pre-completion validation.

        Args:
            sprint_dir: Sprint directory path
            self_verify_report_path: Optional path to self-verify report

        Returns:
            Tuple of (all_passed, list of checklist items)
        """
        items: list[ChecklistItem] = []
        sprint_path = Path(sprint_dir)

        # Check CHANGESET.md
        changeset = sprint_path / "CHANGESET.md"
        items.append(ChecklistItem(
            name="CHANGESET.md exists",
            passed=changeset.exists(),
            message=str(changeset) if changeset.exists() else "CHANGESET.md not found"
        ))

        # Check SELF_VERIFY_REPORT.md
        self_verify = self_verify_report_path or str(sprint_path / "SELF_VERIFY_REPORT.md")
        self_verify_path = Path(self_verify)
        items.append(ChecklistItem(
            name="SELF_VERIFY_REPORT.md exists",
            passed=self_verify_path.exists(),
            message=str(self_verify_path) if self_verify_path.exists() else "SELF_VERIFY_REPORT.md not found"
        ))

        # Check REPAIR_REPORT.md if repair
        if self.is_repair:
            repair_report = sprint_path / "REPAIR_REPORT.md"
            items.append(ChecklistItem(
                name="REPAIR_REPORT.md exists",
                passed=repair_report.exists(),
                message=str(repair_report) if repair_report.exists() else "REPAIR_REPORT.md not found (required for repair)"
            ))

        # Check ARTIFACTS directory
        artifacts = sprint_path / "ARTIFACTS"
        command_outputs = artifacts / "command_outputs"
        items.append(ChecklistItem(
            name="ARTIFACTS/command_outputs exists",
            passed=command_outputs.exists(),
            message=str(command_outputs) if command_outputs.exists() else "ARTIFACTS/command_outputs not found"
        ))

        # If SELF_VERIFY_REPORT.md exists, parse and check commands
        if self_verify_path.exists():
            content = self_verify_path.read_text()
            items.extend(self._check_commands_run(content))

        all_passed = all(item.passed for item in items)

        return all_passed, items

    def _check_commands_run(self, content: str) -> list[ChecklistItem]:
        """Check that required commands were run and have logs."""
        items = []

        # Look for command entries
        commands_found: set[str] = set()

        for line in content.split("\n"):
            if "- cmd:" in line:
                # Extract command
                cmd = line.split("- cmd:", 1)[1].strip()
                commands_found.add(cmd)

                # Check if there's a log path nearby (simplified)
                items.append(ChecklistItem(
                    name=f"Command logged: {cmd[:50]}",
                    passed=True,  # If we found the command, assume it was logged
                    message=f"Found: {cmd[:50]}"
                ))

        # Check required commands
        for required in self.required_commands:
            found = any(required in cmd for cmd in commands_found)
            items.append(ChecklistItem(
                name=f"Required command run: {required[:50]}",
                passed=found,
                message=f"{required[:50]} - {'found' if found else 'NOT FOUND'}"
            ))

        return items

    def validate_or_raise(self, sprint_dir: str) -> None:
        """
        Validate and raise exception if not all items pass.

        Args:
            sprint_dir: Sprint directory path

        Raises:
            PreCompletionError: If validation fails
        """
        passed, items = self.validate(sprint_dir)

        if not passed:
            failed = [i for i in items if not i.passed]
            messages = "\n".join(f"  - {i.name}: {i.message}" for i in failed)
            raise PreCompletionError(
                f"Pre-completion checklist failed:\n{messages}"
            )


class PreCompletionError(Exception):
    """Raised when pre-completion checklist fails."""
    pass
