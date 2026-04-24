"""Generator agent - implements code within contract scope."""

from pathlib import Path
from typing import Optional

from vch.schemas.contract import Contract
from vch.schemas.repair_packet import RepairPacket
from vch.bootstrapper import (
    _APP_JS,
    _INDEX_HTML,
    _PACKAGE_JSON,
    _PLAYWRIGHT_CONFIG,
    _STYLES_CSS,
    _TODO_SPEC,
    _VALIDATE_APP,
)
from vch.tools.command_runner import CommandRunner
from vch.tools.filesystem import GuardedFilesystem


class Generator:
    """
    Generator agent - implements features within contract scope.

    Inputs:
    - CONTRACT.yaml
    - CONTEXT_MANIFEST.yaml
    - must_read files
    - git diff stat
    - REPAIR_PACKET.md (if repair)

    Outputs:
    - Modified code
    - GENERATOR_PLAN.md
    - CHANGESET.md
    - SELF_VERIFY_REPORT.md
    - REPAIR_REPORT.md (if repair)
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.command_runner = CommandRunner(repo_root)

    def invoke(
        self,
        sprint_id: str,
        contract: Contract,
        manifest: Optional[dict] = None,
        repair_packet: Optional[RepairPacket] = None,
    ) -> dict:
        """
        Generate/implement code for a sprint.

        This is a stub implementation. In production, this would
        invoke a DeepAgent with the generator prompt and middleware.

        Args:
            sprint_id: Sprint identifier
            contract: Contract for this sprint
            manifest: Context manifest dict
            repair_packet: Repair packet if this is a repair

        Returns:
            Dict with implementation results
        """
        sprint_dir = self.repo_root / ".harness" / "sprints" / sprint_id
        sprint_dir.mkdir(parents=True, exist_ok=True)

        self._write_generator_plan(sprint_dir, sprint_id, contract, repair_packet)
        changed_files = self._implement_contract(contract)
        command_results = self._run_required_commands(sprint_dir, contract)
        self._write_changeset(sprint_dir, sprint_id, changed_files)
        self._write_self_verify(sprint_dir, sprint_id, command_results)

        if repair_packet:
            self._write_repair_report(sprint_dir, sprint_id, repair_packet)

        return {
            "sprint_id": sprint_id,
            "status": "implemented",
            "generator_plan": str(sprint_dir / "GENERATOR_PLAN.md"),
            "changeset": str(sprint_dir / "CHANGESET.md"),
            "self_verify": str(sprint_dir / "SELF_VERIFY_REPORT.md"),
        }

    def _write_generator_plan(
        self,
        sprint_dir: Path,
        sprint_id: str,
        contract: Contract,
        repair_packet: Optional[RepairPacket]
    ) -> None:
        """Write generator plan."""
        lines = [
            f"# Generator Plan for {sprint_id}",
            "",
            f"## Goal: {contract.goal}",
            "",
            "## Scope",
        ]

        if contract.scope.include:
            lines.append("### Included")
            for path in contract.scope.include:
                lines.append(f"- {path}")

        if contract.scope.exclude:
            lines.append("### Excluded")
            for path in contract.scope.exclude:
                lines.append(f"- {path}")

        if repair_packet:
            lines.append("")
            lines.append("## Repair Context")
            lines.append(f"- Failed AC: {repair_packet.failed_ac}")
            lines.append(f"- Must fix: {', '.join(repair_packet.must_fix)}")
            lines.append(f"- Must not change: {', '.join(repair_packet.must_not_change)}")

        (sprint_dir / "GENERATOR_PLAN.md").write_text("\n".join(lines))

    def _implement_contract(self, contract: Contract) -> list[str]:
        """Implement supported deterministic tasks inside the contract scope."""
        changed_files: list[str] = []
        goal_text = contract.goal.lower()
        allowed = contract.allowed_files
        writer = GuardedFilesystem(str(self.repo_root), allowed)

        if self._is_todo_or_web_task(goal_text):
            desired_files = {
                "package.json": _PACKAGE_JSON,
                "index.html": _INDEX_HTML,
                "playwright.config.mjs": _PLAYWRIGHT_CONFIG,
                "src/app.js": _APP_JS,
                "src/styles.css": _STYLES_CSS,
                "scripts/validate-app.mjs": _VALIDATE_APP,
                "tests/todo.spec.mjs": _TODO_SPEC,
            }
            for path, content in desired_files.items():
                if writer.is_allowed(path):
                    writer.write_text(path, content)
                    changed_files.append(path)

        return changed_files

    def _is_todo_or_web_task(self, goal_text: str) -> bool:
        """Detect tasks covered by the deterministic web generator."""
        return any(token in goal_text for token in ("todo", "待办", "网站", "web", "app"))

    def _run_required_commands(self, sprint_dir: Path, contract: Contract) -> list[dict]:
        """Run required commands and collect self-verification entries."""
        output_dir = sprint_dir / "ARTIFACTS" / "command_outputs"
        results = []
        for command in contract.required_commands:
            result = self.command_runner.run(command, "generator", output_dir)
            results.append({
                "cmd": command,
                "exit_code": result.returncode,
                "log": f"ARTIFACTS/command_outputs/{self._cmd_to_name(command)}.log",
            })
        return results

    def _write_changeset(self, sprint_dir: Path, sprint_id: str, changed_files: list[str]) -> None:
        """Write changeset."""
        files = "\n".join(f"- {path}" for path in changed_files) or "- No files changed"
        content = f"""# Changeset for {sprint_id}

## Summary
Implemented files required by the active sprint contract.

## Files Modified
{files}

## Impact on Acceptance Criteria
The generated files are intended to satisfy the contract acceptance criteria and are verified by required commands.

## Testing Notes
Required commands were run and logged in SELF_VERIFY_REPORT.md.
"""
        (sprint_dir / "CHANGESET.md").write_text(content)

    def _write_self_verify(
        self,
        sprint_dir: Path,
        sprint_id: str,
        command_results: list[dict]
    ) -> None:
        """Write self-verify report."""
        lines = [
            f"# Self Verify Report for {sprint_id}",
            "",
            "## Commands Run",
        ]

        for result in command_results:
            lines.append(f"- cmd: {result['cmd']}")
            lines.append(f"  exit_code: {result['exit_code']}")
            lines.append(f"  log: {result['log']}")

        lines.append("")
        lines.append("## Verification")
        all_passed = all(result["exit_code"] == 0 for result in command_results)
        lines.append(f"- [{'x' if all_passed else ' '}] All required commands passed")
        lines.append("- [x] No forbidden files intentionally modified by generator")

        (sprint_dir / "SELF_VERIFY_REPORT.md").write_text("\n".join(lines))

    def _write_repair_report(
        self,
        sprint_dir: Path,
        sprint_id: str,
        repair_packet: RepairPacket
    ) -> None:
        """Write repair report."""
        content = f"""# Repair Report for {sprint_id}

## Repair Attempt {repair_packet.repair_attempt}

## What was fixed
[TODO: Describe the fix]

## Verification
- [ ] Failed AC now passes
- [ ] Previously passing ACs still pass

## Root Cause (if repeated failure)
[TODO: Analyze root cause]
"""
        (sprint_dir / "REPAIR_REPORT.md").write_text(content)

    def _cmd_to_name(self, cmd: str) -> str:
        """Convert command to file name."""
        import re
        name = re.sub(r'[^a-zA-Z0-9]', '_', cmd)
        return name[:50]
