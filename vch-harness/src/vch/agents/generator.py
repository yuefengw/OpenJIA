"""Generator agent - implements code within contract scope."""

from pathlib import Path
from typing import Optional
import json

from vch.schemas.contract import Contract
from vch.schemas.repair_packet import RepairPacket


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

        # Generate placeholder output files
        self._write_generator_plan(sprint_dir, sprint_id, contract, repair_packet)
        self._write_changeset(sprint_dir, sprint_id)
        self._write_self_verify(sprint_dir, sprint_id, contract)

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

    def _write_changeset(self, sprint_dir: Path, sprint_id: str) -> None:
        """Write changeset."""
        content = f"""# Changeset for {sprint_id}

## Summary
[TODO: Describe what was changed]

## Files Modified
[TODO: List modified files]

## Impact on Acceptance Criteria
[TODO: Map changes to ACs]

## Testing Notes
[TODO: Any testing considerations]
"""
        (sprint_dir / "CHANGESET.md").write_text(content)

    def _write_self_verify(
        self,
        sprint_dir: Path,
        sprint_id: str,
        contract: Contract
    ) -> None:
        """Write self-verify report."""
        artifacts_dir = sprint_dir / "ARTIFACTS" / "command_outputs"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Self Verify Report for {sprint_id}",
            "",
            "## Commands Run",
        ]

        for cmd in contract.required_commands:
            lines.append(f"- cmd: {cmd}")
            lines.append(f"  exit_code: [TODO]")
            lines.append(f"  log: ARTIFACTS/command_outputs/{self._cmd_to_name(cmd)}.log")

        lines.append("")
        lines.append("## Verification")
        lines.append("- [TODO] All required commands passed")
        lines.append("- [TODO] No forbidden files modified")

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
