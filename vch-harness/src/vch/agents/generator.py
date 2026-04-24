"""Generator agent - implements code within contract scope."""

from pathlib import Path
from typing import Optional
import json

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
from vch.llm import LLMBackend, LLMConfigurationError, make_llm_backend


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

    def __init__(
        self,
        repo_root: str,
        llm_backend: Optional[LLMBackend] = None,
        llm_backend_name: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.repo_root = Path(repo_root)
        self.command_runner = CommandRunner(repo_root)
        self.llm_backend = llm_backend
        if self.llm_backend is None and llm_backend_name:
            self.llm_backend = make_llm_backend(llm_backend_name, model)

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
        changed_files = self._implement_contract(contract, manifest, repair_packet)
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

    def _implement_contract(
        self,
        contract: Contract,
        manifest: Optional[dict],
        repair_packet: Optional[RepairPacket],
    ) -> list[str]:
        """Implement supported deterministic tasks inside the contract scope."""
        if self.llm_backend:
            try:
                changed_files = self._implement_with_llm(contract, manifest, repair_packet)
                if changed_files:
                    return changed_files
            except (LLMConfigurationError, ValueError, json.JSONDecodeError, PermissionError) as error:
                self._write_generator_error(contract.sprint_id, error)

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

    def _implement_with_llm(
        self,
        contract: Contract,
        manifest: Optional[dict],
        repair_packet: Optional[RepairPacket],
    ) -> list[str]:
        """Ask an LLM backend for contract-scoped file contents and apply them safely."""
        assert self.llm_backend is not None
        writer = GuardedFilesystem(str(self.repo_root), contract.allowed_files)
        prompt = self._build_llm_prompt(contract, manifest, repair_packet)
        data = self.llm_backend.generate_json(
            instructions=self._load_prompt("generator.md"),
            prompt=prompt,
            schema=_GENERATOR_OUTPUT_SCHEMA,
        )

        files = data.get("files", [])
        if not isinstance(files, list):
            raise ValueError("LLM generator output must include a files array.")

        changed_files = []
        for item in files:
            path = item.get("path")
            content = item.get("content")
            if not path or not isinstance(content, str):
                raise ValueError("Each generated file needs path and content.")
            writer.write_text(path, content)
            changed_files.append(path)

        return changed_files

    def _build_llm_prompt(
        self,
        contract: Contract,
        manifest: Optional[dict],
        repair_packet: Optional[RepairPacket],
    ) -> str:
        """Build the bounded generator prompt."""
        existing_files = {}
        for path in contract.allowed_files:
            candidate = self.repo_root / path
            if candidate.exists() and candidate.is_file():
                existing_files[path] = candidate.read_text(encoding="utf-8", errors="replace")

        packet = {
            "contract": contract.model_dump(),
            "context_manifest": manifest or {},
            "existing_allowed_files": existing_files,
            "repair_packet": repair_packet.model_dump() if repair_packet else None,
            "rules": [
                "Return complete file contents for files you want to create or modify.",
                "Do not include files outside allowed_files.",
                "Do not claim success; the evaluator decides pass or fail.",
                "Prefer the smallest change that satisfies the contract.",
            ],
        }
        return json.dumps(packet, ensure_ascii=False, indent=2)

    def _write_generator_error(self, sprint_id: str, error: Exception) -> None:
        """Persist LLM generator failure before falling back."""
        sprint_dir = self.repo_root / ".harness" / "sprints" / sprint_id
        sprint_dir.mkdir(parents=True, exist_ok=True)
        (sprint_dir / "GENERATOR_ERROR.md").write_text(
            f"# Generator Error\n\nLLM generator failed and deterministic fallback was used.\n\n```text\n{error}\n```\n",
            encoding="utf-8",
        )

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

    def _load_prompt(self, name: str) -> str:
        """Load a role prompt."""
        prompt_path = Path(__file__).parents[1] / "prompts" / name
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8", errors="replace")
        return "You are the VCH Generator. Return valid JSON with contract-scoped files."


_GENERATOR_OUTPUT_SCHEMA = {
    "title": "vch_generator_output",
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "files"],
    "additionalProperties": False,
}
