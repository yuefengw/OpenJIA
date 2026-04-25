"""Tests for evaluator command evidence logging."""

import json

from openjia.agents.evaluator import Evaluator
from openjia.schemas.contract import Contract, Scope


def test_evaluator_records_commands_jsonl_and_evidence(tmp_path):
    (tmp_path / ".harness" / "logs").mkdir(parents=True)
    contract = Contract(
        sprint_id="S001",
        goal="Compile",
        scope=Scope(include=["*.py"], exclude=[]),
        allowed_files=["*.py"],
        forbidden_files=[],
        acceptance_criteria=[
            {
                "id": "AC001",
                "behavior": "Python files compile",
                "verification": {
                    "type": "static_check",
                    "steps": ["python --version"],
                    "oracle": ["command exits 0"],
                    "required_evidence": ["command_output"],
                },
            }
        ],
        required_commands=["python --version"],
        pass_threshold={},
        repair_policy={"max_repair_attempts": 3},
    )

    report = Evaluator(str(tmp_path)).invoke("S001", contract, "HEAD", "HEAD")

    commands_path = tmp_path / ".harness" / "logs" / "commands.jsonl"
    records = [json.loads(line) for line in commands_path.read_text().splitlines()]

    assert report.overall_status == "pass"
    assert records[-1]["cmd"] == "python --version"
    assert records[-1]["exit_code"] == 0
    assert report.criteria[0].evidence


def test_evaluator_rejects_generic_smoke_for_specific_interaction_ac(tmp_path):
    (tmp_path / ".harness" / "logs").mkdir(parents=True)
    (tmp_path / "test-results").mkdir()
    (tmp_path / "test-results" / "page-smoke.txt").write_text(
        "generic browser smoke passed",
        encoding="utf-8",
    )
    contract = Contract(
        sprint_id="S001",
        goal="Build interactive app",
        scope=Scope(include=["index.html"], exclude=[]),
        allowed_files=["index.html"],
        forbidden_files=[],
        acceptance_criteria=[
            {
                "id": "AC001",
                "behavior": "User can drag todo tasks to reorder them",
                "verification": {
                    "type": "e2e",
                    "steps": ["python --version"],
                    "oracle": ["drag reorder interaction works"],
                    "required_evidence": ["command_output"],
                },
            }
        ],
        required_commands=["python --version"],
        pass_threshold={},
        repair_policy={"max_repair_attempts": 3},
    )

    report = Evaluator(str(tmp_path)).invoke("S001", contract, "HEAD", "HEAD")

    assert report.overall_status == "fail"
    assert report.criteria[0].status == "fail"
    assert "criterion-specific runtime evidence" in report.criteria[0].observed
