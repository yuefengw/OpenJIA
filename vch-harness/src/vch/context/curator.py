"""ContextCurator - builds context manifests for sprints and repairs."""

import subprocess
from pathlib import Path
from typing import Optional
import yaml

from vch.context.manifest import ContextManifest
from vch.schemas.contract import Contract
from vch.schemas.eval_report import EvalReport


class ContextCurator:
    """
    Curates context for generator/evaluator invocations.

    Each sprint/repair gets a fresh manifest with only relevant context.
    """

    def build_manifest(
        self,
        sprint_id: str,
        contract: Contract,
        git_base: str,
        git_head: str,
        repo_root: str,
        eval_report: Optional[EvalReport] = None,
        repair_packet: Optional[dict] = None,
    ) -> ContextManifest:
        """
        Build a context manifest for a sprint or repair.

        Args:
            sprint_id: Sprint identifier
            contract: The contract for this sprint
            git_base: Base git commit
            git_head: Current git head
            repo_root: Repository root path
            eval_report: Previous eval report (for repairs)
            repair_packet: Repair packet (for repairs)

        Returns:
            ContextManifest with curated context
        """
        repo_path = Path(repo_root)

        # Collect stable context
        stable_context = self._collect_stable_context(repo_path)

        # Collect current task context
        current_task_context = [
            f".harness/sprints/{sprint_id}/CONTRACT.yaml",
            ".harness/GLOBAL_CONSTRAINTS.md",
        ]

        # Collect relevant code context based on contract
        relevant_code = self._collect_relevant_code_context(
            repo_path, contract.allowed_files
        )

        # Collect failure context if this is a repair
        failure_context: list[str] = []
        latest_failure = None
        if eval_report and eval_report.overall_status != "pass":
            failure_context = self._collect_failure_context(eval_report)
            latest_failure = {
                "eval_report": f".harness/sprints/{sprint_id}/EVAL_REPORT.json",
                "failed_criteria": [
                    c.id for c in eval_report.criteria if c.status == "fail"
                ],
                "evidence": self._collect_evidence_paths(eval_report),
            }

        # Collect state integrity context
        state_context = self._collect_state_integrity_context(repo_path, git_base, git_head)

        # Build manifest
        manifest = ContextManifest(
            sprint_id=sprint_id,
            git_base=git_base,
            git_head=git_head,
            must_read=current_task_context,
            may_read=relevant_code[:20],  # Limit may_read
            forbidden_context=[
                "obsolete eval reports",
                "old unrelated logs",
                "previous generator self-praise",
            ],
            latest_failure=latest_failure,
            allowed_write_paths=contract.allowed_files + [
                f".harness/sprints/{sprint_id}/CHANGESET.md",
                f".harness/sprints/{sprint_id}/SELF_VERIFY_REPORT.md",
            ],
            stable_context=stable_context,
            current_task_context=current_task_context,
            relevant_code_context=relevant_code[:15],
            current_failure_context=failure_context,
            state_integrity_context=state_context,
        )

        return manifest

    def _collect_stable_context(self, repo_path: Path) -> list[str]:
        """Collect stable context files."""
        files = []
        for name in ["AGENTS.md", "PROJECT_RULES.md", "ARCHITECTURE_NOTES.md"]:
            path = repo_path / ".harness" / "memory" / name
            if path.exists():
                files.append(str(path))
        return files

    def _collect_relevant_code_context(
        self,
        repo_path: Path,
        allowed_files: list[str]
    ) -> list[str]:
        """Collect relevant code files based on allowed paths."""
        files = []

        # Add files from allowed_files that exist
        for pattern in allowed_files:
            # Handle glob patterns
            if "*" in pattern:
                matching = list(repo_path.glob(pattern))
                for f in matching:
                    if f.is_file():
                        files.append(str(f))
            else:
                path = repo_path / pattern
                if path.exists() and path.is_file():
                    files.append(str(path))

        return list(set(files))

    def _collect_failure_context(self, eval_report: EvalReport) -> list[str]:
        """Collect context related to current failure."""
        context = []

        # Add evidence paths from failed criteria
        for criterion in eval_report.criteria:
            if criterion.status == "fail":
                context.extend(criterion.evidence)

        # Add log paths
        if eval_report.logs.app_log:
            context.append(eval_report.logs.app_log)
        if eval_report.logs.console_log:
            context.append(eval_report.logs.console_log)

        return list(set(context))

    def _collect_evidence_paths(self, eval_report: EvalReport) -> list[str]:
        """Collect evidence paths from eval report."""
        paths = []
        for criterion in eval_report.criteria:
            paths.extend(criterion.evidence)
        return paths

    def _collect_state_integrity_context(
        self,
        repo_path: Path,
        git_base: str,
        git_head: str
    ) -> list[str]:
        """Collect state integrity context."""
        context = []

        # Get git diff
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", git_base, git_head],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                modified = result.stdout.strip().split("\n")
                context.append(f"Modified files: {len(modified)}")
        except Exception:
            pass

        # Get diff stat
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", git_base, git_head],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                context.append(f"Diff stat:\n{result.stdout}")
        except Exception:
            pass

        return context

    def save_manifest(self, manifest: ContextManifest, sprint_dir: str) -> str:
        """
        Save manifest to YAML file.

        Args:
            manifest: ContextManifest to save
            sprint_dir: Sprint directory path

        Returns:
            Path to saved manifest
        """
        path = Path(sprint_dir) / "CONTEXT_MANIFEST.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(manifest.model_dump(), f, default_flow_style=False)

        return str(path)
