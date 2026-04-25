"""Helpers for FEATURE_LEDGER.json and PROGRESS.md."""

from pathlib import Path
import json

from openjia.schemas.eval_report import EvalReport
from openjia.schemas.feature_ledger import (
    FeatureLedger,
    LedgerAcceptanceCriterion,
    LedgerFeature,
)
from openjia.schemas.feature_spec import FeatureSpec


def build_ledger_from_spec(spec: FeatureSpec) -> FeatureLedger:
    """Create a feature ledger from a planner feature spec."""
    sprint_by_feature: dict[str, str] = {}
    for sprint in spec.sprints:
        for feature_id in sprint.features:
            sprint_by_feature[feature_id] = sprint.id

    features = []
    for feature in spec.features:
        features.append(
            LedgerFeature(
                id=feature.id,
                title=feature.title,
                sprint_id=sprint_by_feature.get(feature.id),
                acceptance_criteria=[
                    LedgerAcceptanceCriterion(
                        id=ac.id,
                        description=ac.description,
                        verification_type=ac.verification_type,
                        oracle=ac.oracle,
                        required_evidence=ac.required_evidence,
                    )
                    for ac in feature.acceptance_criteria
                ],
            )
        )

    return FeatureLedger(project_goal=spec.project_goal, features=features)


def load_ledger(path: Path) -> FeatureLedger:
    """Load FEATURE_LEDGER.json."""
    return FeatureLedger(**json.loads(path.read_text()))


def save_ledger(ledger: FeatureLedger, path: Path) -> None:
    """Save FEATURE_LEDGER.json."""
    path.write_text(json.dumps(ledger.model_dump(), indent=2))


def update_ledger_from_eval(ledger: FeatureLedger, eval_report: EvalReport) -> FeatureLedger:
    """Apply evaluator results to the ledger."""
    results = {criterion.id: criterion for criterion in eval_report.criteria}

    for feature in ledger.features:
        if feature.sprint_id and feature.sprint_id != eval_report.sprint_id:
            continue

        for ac in feature.acceptance_criteria:
            result = results.get(ac.id)
            if not result:
                continue
            ac.status = result.status
            ac.evidence = result.evidence
            ac.latest_failure = result.observed if result.status == "fail" else None

        statuses = {ac.status for ac in feature.acceptance_criteria}
        if statuses and statuses <= {"pass"}:
            feature.status = "pass"
        elif "fail" in statuses:
            feature.status = "fail"
        elif "blocked" in statuses:
            feature.status = "blocked"
        elif "pass" in statuses:
            feature.status = "in_progress"

    return ledger


def write_progress_markdown(ledger: FeatureLedger, path: Path) -> None:
    """Write a human-readable progress file."""
    lines = ["# Progress", "", f"Goal: {ledger.project_goal}", ""]

    for feature in ledger.features:
        lines.append(f"## {feature.id}: {feature.title}")
        lines.append(f"- Sprint: {feature.sprint_id or 'unassigned'}")
        lines.append(f"- Status: {feature.status}")
        lines.append("")
        lines.append("### Acceptance Criteria")
        for ac in feature.acceptance_criteria:
            lines.append(f"- [{_checkbox(ac.status)}] {ac.id}: {ac.description}")
            lines.append(f"  - Status: {ac.status}")
            lines.append(f"  - Oracle: {ac.oracle}")
            if ac.evidence:
                lines.append(f"  - Evidence: {', '.join(ac.evidence)}")
            if ac.latest_failure:
                lines.append(f"  - Latest failure: {ac.latest_failure}")
        lines.append("")

    path.write_text("\n".join(lines))


def _checkbox(status: str) -> str:
    return "x" if status == "pass" else " "
