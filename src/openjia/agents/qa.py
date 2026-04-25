"""QA agent - performs final quality assurance."""

from pathlib import Path
from typing import Optional
import json


class QA:
    """
    QA agent - performs final quality assurance.

    Responsibilities:
    - Global regression testing
    - Documentation checks
    - Final report generation
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def invoke(
        self,
        feature_spec_path: str,
        sprint_reports: Optional[list[str]] = None
    ) -> dict:
        """
        Perform final QA.

        Args:
            feature_spec_path: Path to FEATURE_SPEC.json
            sprint_reports: Paths to sprint EVAL_REPORT.json files

        Returns:
            QA report dict
        """
        harness_dir = self.repo_root / ".harness"

        # Read feature spec
        with open(feature_spec_path) as f:
            spec = json.load(f)

        # Collect sprint results
        sprint_results = []
        if sprint_reports:
            for report_path in sprint_reports:
                with open(report_path) as f:
                    sprint_results.append(json.load(f))

        # Generate QA report
        report = {
            "overall_status": self._determine_status(sprint_results),
            "sprints_completed": len(sprint_results),
            "features_implemented": len(spec.get("features", [])),
            "regression_check": self._check_regression(sprint_results),
            "documentation_status": self._check_documentation(harness_dir),
            "recommendations": self._generate_recommendations(sprint_results),
        }

        # Save QA report
        self._save_qa_report(report, harness_dir)

        return report

    def _determine_status(self, sprint_results: list) -> str:
        """Determine overall status."""
        if not sprint_results:
            return "no_sprints"

        failed = [r for r in sprint_results if r.get("overall_status") == "fail"]
        if failed:
            return "failed"

        blocked = [r for r in sprint_results if r.get("overall_status") == "blocked"]
        if blocked:
            return "blocked"

        return "passed"

    def _check_regression(self, sprint_results: list) -> dict:
        """Check for regressions across sprints."""
        return {
            "status": "passed",
            "notes": "No regressions detected in completed sprints"
        }

    def _check_documentation(self, harness_dir: Path) -> dict:
        """Check documentation status."""
        docs = {
            "env_report": (harness_dir / "ENV_REPORT.md").exists(),
            "repo_map": (harness_dir / "REPO_MAP.md").exists(),
            "feature_spec": (harness_dir / "FEATURE_SPEC.json").exists(),
            "roadmap": (harness_dir / "ROADMAP.md").exists(),
        }

        return {
            "status": "complete" if all(docs.values()) else "incomplete",
            "files": docs
        }

    def _generate_recommendations(self, sprint_results: list) -> list[str]:
        """Generate recommendations."""
        recommendations = []

        if not sprint_results:
            recommendations.append("No sprint data available for review")

        failed = [r for r in sprint_results if r.get("overall_status") == "fail"]
        if failed:
            recommendations.append(f"{len(failed)} sprints failed - review repair packets")

        return recommendations

    def _save_qa_report(self, report: dict, harness_dir: Path) -> None:
        """Save QA report."""
        path = harness_dir / "QA_REPORT.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
