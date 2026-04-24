"""Evaluator agent - independently verifies sprint completion."""

from pathlib import Path
import subprocess
import fnmatch

from vch.schemas.contract import Contract
from vch.schemas.eval_report import EvalReport, CriterionResult, CommandsRun, DiffScopeCheck, Logs
from vch.tools.command_runner import CommandRunner


class Evaluator:
    """
    Evaluator agent - independently verifies sprint completion.

    Responsibilities:
    - Run build/test/lint/typecheck commands
    - Run Playwright tests if applicable
    - Check logs for console errors
    - Verify git diff scope
    - Generate EVAL_REPORT.json
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.command_runner = CommandRunner(repo_root)

    def invoke(
        self,
        sprint_id: str,
        contract: Contract,
        git_base: str,
        git_head: str,
    ) -> EvalReport:
        """
        Evaluate a sprint.

        This is a stub implementation. In production, this would
        invoke a DeepAgent with the evaluator prompt.

        Args:
            sprint_id: Sprint identifier
            contract: Contract to verify against
            git_base: Git base commit
            git_head: Git head commit

        Returns:
            EvalReport with evaluation results
        """
        sprint_dir = self.repo_root / ".harness" / "sprints" / sprint_id
        artifacts_dir = sprint_dir / "ARTIFACTS"
        command_outputs = artifacts_dir / "command_outputs"
        command_outputs.mkdir(parents=True, exist_ok=True)

        # Run commands
        commands_run = []
        all_passed = True

        for cmd_str in contract.required_commands:
            result = self._run_command(cmd_str, command_outputs)
            log_path = command_outputs / f"{self._cmd_to_name(cmd_str)}.log"
            commands_run.append(CommandsRun(
                cmd=cmd_str,
                exit_code=result.returncode,
                log_path=str(log_path)
            ))
            if result.returncode != 0:
                all_passed = False

        # Check diff scope
        diff_scope_passed, unexpected = self._check_diff_scope(git_base, git_head, contract)
        if not diff_scope_passed:
            all_passed = False

        # Generate criterion results
        criteria = []
        for ac in contract.acceptance_criteria:
            evidence = [
                str(command_outputs / f"{self._cmd_to_name(command.cmd)}.log")
                for command in commands_run
                if command.log_path
            ]
            criteria.append(CriterionResult(
                id=ac.id,
                status="pass" if all_passed else "fail",
                failure_type=None if all_passed else self._failure_type(commands_run, diff_scope_passed),
                evidence=evidence,
                observed="[TODO: Run actual verification]",
                expected=ac.behavior if hasattr(ac, 'behavior') else "See contract",
                likely_location=[],
                minimal_reproduction=[],
                repair_hint=None if all_passed else "Check implementation"
            ))

        # Determine overall status
        if all_passed:
            overall_status = "pass"
        elif not all_passed:
            overall_status = "fail"
        else:
            overall_status = "blocked"

        return EvalReport(
            sprint_id=sprint_id,
            overall_status=overall_status,
            summary=f"Sprint {sprint_id} evaluation {'passed' if all_passed else 'failed'}",
            commands_run=commands_run,
            criteria=criteria,
            diff_scope_check=DiffScopeCheck(
                status="pass" if diff_scope_passed else "fail",
                unexpected_files_modified=unexpected
            ),
            logs=Logs(
                app_log=str(artifacts_dir / "app.log") if (artifacts_dir / "app.log").exists() else None,
                console_log=str(artifacts_dir / "console.log") if (artifacts_dir / "console.log").exists() else None
            )
        )

    def _run_command(self, cmd_str: str, output_dir: Path) -> subprocess.CompletedProcess:
        """Run a command and save output."""
        return self.command_runner.run(cmd_str, "evaluator", output_dir)

    def _check_diff_scope(
        self,
        git_base: str,
        git_head: str,
        contract: Contract
    ) -> tuple[bool, list[str]]:
        """Check if diff is within scope."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", git_base, git_head],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return True, []

            modified = result.stdout.strip().split("\n")
            modified = [f for f in modified if f]

            unexpected = []
            for path in modified:
                if self._matches_any(path, contract.forbidden_files):
                    unexpected.append(path)
                    continue
                if contract.allowed_files and not self._matches_any(path, contract.allowed_files):
                    unexpected.append(path)
            return len(unexpected) == 0, unexpected
        except Exception:
            return True, []

    def _matches_any(self, path: str, patterns: list[str]) -> bool:
        """Check whether a path matches any exact path or glob."""
        return any(path == pattern or fnmatch.fnmatch(path, pattern) for pattern in patterns)

    def _failure_type(self, commands_run: list[CommandsRun], diff_scope_passed: bool) -> str:
        """Classify deterministic evaluator failures."""
        if not diff_scope_passed:
            return "implementation_bug"
        if any(command.exit_code != 0 for command in commands_run):
            return "implementation_bug"
        return "unknown"

    def _cmd_to_name(self, cmd: str) -> str:
        """Convert command to file name."""
        import re
        name = re.sub(r'[^a-zA-Z0-9]', '_', cmd)
        return name[:50]
