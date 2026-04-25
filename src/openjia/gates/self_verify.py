"""SelfVerifyGate - validates generator's self-verification."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import re


@dataclass
class SelfVerifyIssue:
    """An issue found during self-verification check."""

    rule: str
    severity: str  # error, warning
    message: str
    location: Optional[str] = None


@dataclass
class SelfVerifyResult:
    """Result of self-verification check."""

    passed: bool
    issues: list[SelfVerifyIssue]
    commands_run: list[str]
    logs_saved: list[str]


class SelfVerifyGate:
    """
    Validates that the Generator properly ran required commands
    and saved logs before completing.

    Checks:
    - All required_commands were run
    - Each command has exit code and log path
    - CHANGESET.md exists
    - SELF_VERIFY_REPORT.md exists
    - If repair, REPAIR_REPORT.md exists
    """

    def validate(
        self,
        contract_path: Optional[str] = None,
        required_commands: Optional[list[str]] = None,
        is_repair: bool = False,
        sprint_dir: Optional[str] = None
    ) -> SelfVerifyResult:
        """
        Validate self-verification.

        Args:
            contract_path: Path to CONTRACT.yaml
            required_commands: List of commands that should have run
            is_repair: Whether this is a repair attempt
            sprint_dir: Sprint directory path

        Returns:
            SelfVerifyResult with validation status
        """
        issues: list[SelfVerifyIssue] = []
        commands_run: list[str] = []
        logs_saved: list[str] = []

        if sprint_dir:
            sprint_path = Path(sprint_dir)

            # Check CHANGESET.md
            changeset_path = sprint_path / "CHANGESET.md"
            if not changeset_path.exists():
                issues.append(SelfVerifyIssue(
                    "required_artifacts",
                    "error",
                    "CHANGESET.md not found",
                    location=str(changeset_path)
                ))

            # Check SELF_VERIFY_REPORT.md
            self_verify_path = sprint_path / "SELF_VERIFY_REPORT.md"
            if not self_verify_path.exists():
                issues.append(SelfVerifyIssue(
                    "required_artifacts",
                    "error",
                    "SELF_VERIFY_REPORT.md not found",
                    location=str(self_verify_path)
                ))
            else:
                content = self_verify_path.read_text()
                parsed_commands = self._parse_commands(content)
                commands_run.extend(entry["cmd"] for entry in parsed_commands)

                for entry in parsed_commands:
                    cmd = entry["cmd"]
                    exit_code = entry.get("exit_code")
                    log_path = entry.get("log")

                    if exit_code is None:
                        issues.append(SelfVerifyIssue(
                            "command_exit_code",
                            "error",
                            f"Command has no numeric exit_code: {cmd}",
                            location="SELF_VERIFY_REPORT.md"
                        ))
                    elif exit_code != 0:
                        issues.append(SelfVerifyIssue(
                            "command_exit_code",
                            "error",
                            f"Command failed self verification: {cmd} exited {exit_code}",
                            location="SELF_VERIFY_REPORT.md"
                        ))

                    if not log_path:
                        issues.append(SelfVerifyIssue(
                            "command_log",
                            "error",
                            f"Command has no log path: {cmd}",
                            location="SELF_VERIFY_REPORT.md"
                        ))
                    else:
                        resolved_log = Path(log_path)
                        if not resolved_log.is_absolute():
                            resolved_log = sprint_path / resolved_log
                        if not resolved_log.exists():
                            issues.append(SelfVerifyIssue(
                                "command_log",
                                "error",
                                f"Command log does not exist: {log_path}",
                                location=str(resolved_log)
                            ))

            # Check REPAIR_REPORT.md if repair
            if is_repair:
                repair_report_path = sprint_path / "REPAIR_REPORT.md"
                if not repair_report_path.exists():
                    issues.append(SelfVerifyIssue(
                        "required_artifacts",
                        "error",
                        "REPAIR_REPORT.md not found for repair attempt",
                        location=str(repair_report_path)
                    ))

            # Check ARTIFACTS directory
            artifacts_dir = sprint_path / "ARTIFACTS"
            if artifacts_dir.exists():
                command_outputs = artifacts_dir / "command_outputs"
                if command_outputs.exists():
                    for log_file in command_outputs.glob("*.log"):
                        logs_saved.append(str(log_file))

        # Check required commands
        if required_commands:
            missing_commands = [c for c in required_commands if c not in commands_run]
            for cmd in missing_commands:
                issues.append(SelfVerifyIssue(
                    "required_commands",
                    "error",
                    f"Required command not run: {cmd}",
                    location="SELF_VERIFY_REPORT.md"
                ))

        errors = [i for i in issues if i.severity == "error"]

        return SelfVerifyResult(
            passed=len(errors) == 0,
            issues=issues,
            commands_run=commands_run,
            logs_saved=logs_saved
        )

    def _parse_commands(self, content: str) -> list[dict]:
        """Parse command entries from SELF_VERIFY_REPORT.md."""
        entries: list[dict] = []
        current: Optional[dict] = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("- cmd:"):
                if current:
                    entries.append(current)
                current = {"cmd": line.split("- cmd:", 1)[1].strip()}
                continue

            if current is None:
                continue

            if line.startswith("exit_code:"):
                raw_value = line.split(":", 1)[1].strip()
                if re.fullmatch(r"-?\d+", raw_value):
                    current["exit_code"] = int(raw_value)
                else:
                    current["exit_code"] = None
            elif line.startswith("log:"):
                current["log"] = line.split(":", 1)[1].strip()

        if current:
            entries.append(current)

        return entries
