"""Planner agent - generates feature specs and roadmaps."""

from pathlib import Path
from typing import Optional
import json

from vch.schemas.feature_spec import FeatureSpec


class Planner:
    """
    Planner agent - converts user requirements into verifiable task graphs.

    Inputs:
    - User task
    - ENV_REPORT.md
    - REPO_MAP.md
    - GLOBAL_CONSTRAINTS.md
    - KNOWN_FAILURES.md

    Outputs:
    - FEATURE_SPEC.json
    - ROADMAP.md
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def invoke(
        self,
        user_task: str,
        env_report_path: Optional[str] = None,
        repo_map_path: Optional[str] = None,
        constraints_path: Optional[str] = None,
        failures_path: Optional[str] = None,
    ) -> FeatureSpec:
        """
        Generate a feature spec from user task.

        This is a stub implementation. In production, this would
        invoke a DeepAgent with the planner prompt.

        Args:
            user_task: User's task description
            env_report_path: Path to ENV_REPORT.md
            repo_map_path: Path to REPO_MAP.md
            constraints_path: Path to GLOBAL_CONSTRAINTS.md
            failures_path: Path to KNOWN_FAILURES.md

        Returns:
            FeatureSpec object
        """
        # Read input files
        env_report = ""
        if env_report_path and Path(env_report_path).exists():
            env_report = Path(env_report_path).read_text()

        repo_map = ""
        if repo_map_path and Path(repo_map_path).exists():
            repo_map = Path(repo_map_path).read_text()

        constraints = ""
        if constraints_path and Path(constraints_path).exists():
            constraints = Path(constraints_path).read_text()

        # In a real implementation, this would call a DeepAgent
        # For now, generate a placeholder spec
        spec = self._generate_placeholder_spec(user_task)

        # Save the spec
        harness_dir = self.repo_root / ".harness"
        self._save_feature_spec(spec, harness_dir)
        self._save_roadmap(spec, harness_dir)

        return spec

    def _generate_placeholder_spec(self, user_task: str) -> FeatureSpec:
        """Generate a placeholder feature spec."""
        return FeatureSpec(
            project_goal=user_task,
            non_goals=[],
            assumptions=[f"User requested: {user_task}"],
            features=[],
            sprints=[],
        )

    def _save_feature_spec(self, spec: FeatureSpec, harness_dir: Path) -> str:
        """Save feature spec to JSON."""
        path = harness_dir / "FEATURE_SPEC.json"
        with open(path, "w") as f:
            json.dump(spec.model_dump(), f, indent=2)
        return str(path)

    def _save_roadmap(self, spec: FeatureSpec, harness_dir: Path) -> None:
        """Save roadmap to markdown."""
        lines = ["# Roadmap", "", f"## Project Goal: {spec.project_goal}", ""]

        for sprint in spec.sprints:
            lines.append(f"## {sprint.id}: {sprint.goal}")
            lines.append("")
            lines.append("### Features")
            for fid in sprint.features:
                lines.append(f"- {fid}")
            lines.append("")
            lines.append("### Verification Commands")
            for cmd in sprint.verification_commands:
                lines.append(f"```bash\n{cmd}\n```")
            lines.append("")

        (harness_dir / "ROADMAP.md").write_text("\n".join(lines))
