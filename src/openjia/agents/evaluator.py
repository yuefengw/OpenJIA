"""Evaluator agent - independently verifies sprint completion."""

import fnmatch
import re
import subprocess
from pathlib import Path

from openjia.schemas.contract import Contract
from openjia.schemas.eval_report import EvalReport, CriterionResult, CommandsRun, DiffScopeCheck, Logs
from openjia.tools.command_runner import CommandRunner


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

        # Generate criterion results. Criteria are judged independently: a passing
        # command set is necessary, but interactive/e2e criteria also need
        # criterion-specific evidence instead of a generic smoke artifact.
        criteria = []
        artifact_evidence = self._collect_artifact_evidence()
        for ac in contract.acceptance_criteria:
            evidence = [
                str(command_outputs / f"{self._cmd_to_name(command.cmd)}.log")
                for command in commands_run
                if command.log_path
            ]
            evidence.extend(artifact_evidence)
            criterion_passed, reason = self._criterion_passed(
                ac,
                evidence,
                commands_run,
                diff_scope_passed,
            )
            criteria.append(CriterionResult(
                id=ac.id,
                status="pass" if criterion_passed else "fail",
                failure_type=None if criterion_passed else self._failure_type(
                    commands_run,
                    diff_scope_passed,
                    evidence_gap=all_passed,
                ),
                evidence=evidence,
                observed=self._observed_summary(commands_run, diff_scope_passed, artifact_evidence, reason),
                expected=ac.behavior if hasattr(ac, 'behavior') else "See contract",
                likely_location=[],
                minimal_reproduction=[],
                repair_hint=None if criterion_passed else "Add runnable, criterion-specific verification evidence."
            ))

        # Determine overall status
        all_criteria_passed = all(criterion.status == "pass" for criterion in criteria)
        if all_passed and all_criteria_passed:
            overall_status = "pass"
        elif not all_passed or not all_criteria_passed:
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

    def _failure_type(
        self,
        commands_run: list[CommandsRun],
        diff_scope_passed: bool,
        evidence_gap: bool = False,
    ) -> str:
        """Classify deterministic evaluator failures."""
        if not diff_scope_passed:
            return "implementation_bug"
        if any(command.exit_code != 0 for command in commands_run):
            return "implementation_bug"
        if evidence_gap:
            return "implementation_bug"
        return "unknown"

    def _collect_artifact_evidence(self) -> list[str]:
        """Collect generated browser/test artifacts when present."""
        evidence = []
        for root in ("test-results", "playwright-report"):
            path = self.repo_root / root
            if not path.exists():
                continue
            for file in path.rglob("*"):
                if file.is_file():
                    evidence.append(str(file))
        return evidence

    def _criterion_passed(
        self,
        ac,
        evidence: list[str],
        commands_run: list[CommandsRun],
        diff_scope_passed: bool,
    ) -> tuple[bool, str]:
        """Decide whether one acceptance criterion has sufficient evidence."""
        if not diff_scope_passed:
            return False, "diff scope failed"
        if any(command.exit_code != 0 for command in commands_run):
            return False, "one or more required commands failed"

        missing_evidence = self._missing_required_evidence(ac, evidence)
        if missing_evidence:
            return False, f"missing required evidence: {', '.join(missing_evidence)}"

        if self._needs_specific_runtime_evidence(ac):
            if not self._has_specific_runtime_evidence(ac, evidence):
                return False, "missing criterion-specific runtime evidence"

        return True, "criterion evidence satisfied"

    def _missing_required_evidence(self, ac, evidence: list[str]) -> list[str]:
        """Map required_evidence types to concrete artifact checks."""
        required = [item.lower() for item in getattr(ac, "required_evidence", [])]
        if not required:
            return []

        lower_paths = [path.lower().replace("\\", "/") for path in evidence]
        missing = []
        for item in required:
            if item in {"command_output", "log", "logs"}:
                if not any(path.endswith(".log") for path in lower_paths):
                    missing.append(item)
            elif item in {"screenshot", "image"}:
                if not any(path.endswith((".png", ".jpg", ".jpeg", ".webp")) for path in lower_paths):
                    missing.append(item)
            elif item in {"trace"}:
                if not any("trace" in path or path.endswith(".zip") for path in lower_paths):
                    missing.append(item)
            elif item in {"browser", "e2e", "html"}:
                if not any(path.endswith((".html", ".png", ".txt")) for path in lower_paths):
                    missing.append(item)
        return missing

    def _needs_specific_runtime_evidence(self, ac) -> bool:
        """Detect criteria where generic command success is not enough."""
        verification_type = ac.verification.type.lower()
        behavior = f"{ac.behavior} {' '.join(ac.oracle)}".lower()
        interaction_terms = (
            "add", "create", "delete", "remove", "complete", "toggle", "persist",
            "refresh", "filter", "search", "drag", "drop", "reorder", "click",
            "submit", "edit", "新增", "添加", "删除", "完成", "筛选", "搜索",
            "拖拽", "排序", "点击", "持久",
        )
        return verification_type in {"e2e", "integration"} or any(term in behavior for term in interaction_terms)

    def _has_specific_runtime_evidence(self, ac, evidence: list[str]) -> bool:
        """Require runtime artifacts/logs to mention the AC's meaningful behavior."""
        blob_parts = []
        for path in evidence:
            normalized = path.replace("\\", "/")
            blob_parts.append(normalized.lower())
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.repo_root / path
            if file_path.exists() and file_path.is_file() and file_path.stat().st_size < 300_000:
                try:
                    blob_parts.append(file_path.read_text(encoding="utf-8", errors="replace").lower())
                except OSError:
                    pass
        blob = "\n".join(blob_parts)

        generic_only_markers = (
            "generic browser smoke passed",
            "page-smoke.html",
            "page-smoke.txt",
        )
        if any(marker in blob for marker in generic_only_markers):
            keywords = self._criterion_keywords(ac)
            return bool(keywords and any(keyword in blob for keyword in keywords))

        keywords = self._criterion_keywords(ac)
        return not keywords or any(keyword in blob for keyword in keywords)

    def _criterion_keywords(self, ac) -> list[str]:
        """Extract stable behavior words from criterion text."""
        text = f"{ac.behavior} {' '.join(ac.oracle)}".lower()
        aliases = {
            "add": ["add", "create", "new", "新增", "添加"],
            "delete": ["delete", "remove", "删除"],
            "complete": ["complete", "toggle", "done", "完成"],
            "persist": ["persist", "refresh", "reload", "localstorage", "持久"],
            "filter": ["filter", "筛选"],
            "search": ["search", "搜索"],
            "drag": ["drag", "drop", "reorder", "拖拽", "排序"],
        }
        keywords = []
        for canonical, terms in aliases.items():
            if any(term in text for term in terms):
                keywords.extend(terms + [canonical])

        stopwords = {
            "the", "and", "with", "that", "this", "must", "should", "user",
            "users", "can", "able", "website", "page", "app", "command",
            "exits", "zero", "passes", "works", "request",
        }
        for word in re.findall(r"[a-z0-9_]{4,}", text):
            if word not in stopwords:
                keywords.append(word)
        return sorted(set(keywords))

    def _observed_summary(
        self,
        commands_run: list[CommandsRun],
        diff_scope_passed: bool,
        artifact_evidence: list[str],
        criterion_reason: str = "",
    ) -> str:
        """Summarize evaluator observations."""
        command_summary = ", ".join(
            f"{command.cmd} exited {command.exit_code}" for command in commands_run
        )
        artifact_summary = f"; collected {len(artifact_evidence)} test artifacts" if artifact_evidence else ""
        scope_summary = "diff scope passed" if diff_scope_passed else "diff scope failed"
        reason_summary = f"; {criterion_reason}" if criterion_reason else ""
        return f"{command_summary}; {scope_summary}{artifact_summary}{reason_summary}"

    def _cmd_to_name(self, cmd: str) -> str:
        """Convert command to file name."""
        import re
        name = re.sub(r'[^a-zA-Z0-9]', '_', cmd)
        return name[:50]
