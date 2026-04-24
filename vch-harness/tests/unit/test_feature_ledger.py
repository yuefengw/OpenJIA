"""Tests for feature ledger progress tracking."""

from vch.feature_ledger import build_ledger_from_spec, update_ledger_from_eval
from vch.schemas.eval_report import EvalReport
from vch.schemas.feature_spec import AcceptanceCriterion, Feature, FeatureSpec, Sprint


def test_builds_ledger_from_feature_spec():
    spec = FeatureSpec(
        project_goal="Add login",
        features=[
            Feature(
                id="F001",
                title="Login",
                user_value="Users can sign in",
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Login form submits",
                        verification_type="unit",
                        oracle="test passes",
                        required_evidence=["command_output"],
                    )
                ],
            )
        ],
        sprints=[Sprint(id="S001", goal="Login", features=["F001"], verification_commands=["npm test"])],
    )

    ledger = build_ledger_from_spec(spec)

    assert ledger.project_goal == "Add login"
    assert ledger.features[0].sprint_id == "S001"
    assert ledger.features[0].acceptance_criteria[0].status == "pending"


def test_updates_ledger_from_eval_report():
    spec = FeatureSpec(
        project_goal="Add login",
        features=[
            Feature(
                id="F001",
                title="Login",
                user_value="Users can sign in",
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Login form submits",
                        verification_type="unit",
                        oracle="test passes",
                        required_evidence=["command_output"],
                    )
                ],
            )
        ],
        sprints=[Sprint(id="S001", goal="Login", features=["F001"], verification_commands=["npm test"])],
    )
    ledger = build_ledger_from_spec(spec)
    eval_report = EvalReport(
        sprint_id="S001",
        overall_status="pass",
        summary="ok",
        commands_run=[],
        criteria=[
            {
                "id": "AC001",
                "status": "pass",
                "failure_type": None,
                "evidence": [".harness/sprints/S001/ARTIFACTS/command_outputs/npm_test.log"],
                "observed": "passed",
                "expected": "test passes",
                "likely_location": [],
                "minimal_reproduction": [],
                "repair_hint": None,
            }
        ],
        diff_scope_check={"status": "pass", "unexpected_files_modified": []},
        logs={},
    )

    update_ledger_from_eval(ledger, eval_report)

    assert ledger.features[0].status == "pass"
    assert ledger.features[0].acceptance_criteria[0].status == "pass"
    assert ledger.features[0].acceptance_criteria[0].evidence
