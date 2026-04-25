"""Tests for acceptance coverage gate."""

from vch.gates.acceptance_coverage import AcceptanceCoverageGate
from vch.schemas.contract import Contract, Scope
from vch.schemas.eval_report import EvalReport


def _contract() -> Contract:
    return Contract(
        sprint_id="S001",
        goal="Test",
        scope=Scope(include=["src/app.js"], exclude=[]),
        allowed_files=["src/app.js"],
        forbidden_files=[],
        acceptance_criteria=[
            {
                "id": "AC001",
                "behavior": "works",
                "verification": {
                    "type": "unit",
                    "steps": ["npm test"],
                    "oracle": ["test passes"],
                    "required_evidence": ["command_output"],
                },
            }
        ],
        required_commands=["npm test"],
        pass_threshold={},
        repair_policy={"max_repair_attempts": 3},
    )


def test_acceptance_coverage_rejects_pass_without_evidence():
    report = EvalReport(
        sprint_id="S001",
        overall_status="pass",
        summary="claimed pass",
        commands_run=[{"cmd": "npm test", "exit_code": 0, "log_path": "test.log"}],
        criteria=[
            {
                "id": "AC001",
                "status": "pass",
                "failure_type": None,
                "evidence": [],
                "observed": "npm test exited 0",
                "expected": "works",
                "likely_location": [],
                "minimal_reproduction": [],
                "repair_hint": None,
            }
        ],
        diff_scope_check={"status": "pass", "unexpected_files_modified": []},
        logs={},
    )

    result = AcceptanceCoverageGate().validate(_contract(), report)

    assert result.passed is False
    assert any(issue.rule == "missing_evidence" for issue in result.issues)


def test_acceptance_coverage_accepts_evidenced_pass():
    report = EvalReport(
        sprint_id="S001",
        overall_status="pass",
        summary="pass",
        commands_run=[{"cmd": "npm test", "exit_code": 0, "log_path": "test.log"}],
        criteria=[
            {
                "id": "AC001",
                "status": "pass",
                "failure_type": None,
                "evidence": ["test.log"],
                "observed": "npm test exited 0",
                "expected": "works",
                "likely_location": [],
                "minimal_reproduction": [],
                "repair_hint": None,
            }
        ],
        diff_scope_check={"status": "pass", "unexpected_files_modified": []},
        logs={},
    )

    result = AcceptanceCoverageGate().validate(_contract(), report)

    assert result.passed is True
