"""Unit tests for EvalReport schema."""

import pytest
from vch.schemas.eval_report import EvalReport, CriterionResult, CommandsRun, DiffScopeCheck, Logs


class TestEvalReport:
    """Tests for EvalReport schema."""

    def test_valid_eval_report(self):
        """Test creating a valid eval report."""
        report = EvalReport(
            sprint_id="S001",
            overall_status="pass",
            summary="All tests passed",
            commands_run=[
                CommandsRun(cmd="npm test", exit_code=0, log_path="test.log")
            ],
            criteria=[
                CriterionResult(
                    id="AC001",
                    status="pass",
                    failure_type=None,
                    evidence=["test.log"],
                    observed="Tests passed",
                    expected="Tests pass",
                    likely_location=["src/app.ts"],
                    minimal_reproduction=[],
                    repair_hint=None
                )
            ],
            diff_scope_check=DiffScopeCheck(
                status="pass",
                unexpected_files_modified=[]
            ),
            logs=Logs(app_log="app.log", console_log="console.log")
        )

        assert report.sprint_id == "S001"
        assert report.overall_status == "pass"
        assert len(report.criteria) == 1

    def test_fail_status(self):
        """Test eval report with fail status."""
        report = EvalReport(
            sprint_id="S001",
            overall_status="fail",
            summary="Tests failed",
            commands_run=[
                CommandsRun(cmd="npm test", exit_code=1, log_path="test.log")
            ],
            criteria=[
                CriterionResult(
                    id="AC001",
                    status="fail",
                    failure_type="implementation_bug",
                    evidence=["test.log"],
                    observed="Assertion failed",
                    expected="All assertions pass",
                    likely_location=["src/app.ts"],
                    minimal_reproduction=["Run npm test"],
                    repair_hint="Check the assertion"
                )
            ],
            diff_scope_check=DiffScopeCheck(
                status="pass",
                unexpected_files_modified=[]
            ),
            logs=Logs(app_log=None, console_log=None)
        )

        assert report.overall_status == "fail"
        assert report.criteria[0].failure_type == "implementation_bug"

    def test_infrastructure_failure(self):
        """Test infrastructure failure status."""
        report = EvalReport(
            sprint_id="S001",
            overall_status="infrastructure_failure",
            summary="Could not start dev server",
            commands_run=[
                CommandsRun(cmd="npm run dev", exit_code=1, log_path="dev.log")
            ],
            criteria=[],
            diff_scope_check=DiffScopeCheck(status="pass", unexpected_files_modified=[]),
            logs=Logs(app_log=None, console_log=None)
        )

        assert report.overall_status == "infrastructure_failure"

    def test_blocked_status(self):
        """Test blocked status."""
        report = EvalReport(
            sprint_id="S001",
            overall_status="blocked",
            summary="Sprint is blocked - contract gap",
            commands_run=[],
            criteria=[],
            diff_scope_check=DiffScopeCheck(status="pass", unexpected_files_modified=[]),
            logs=Logs(app_log=None, console_log=None)
        )

        assert report.overall_status == "blocked"

    def test_diff_scope_check_fail(self):
        """Test diff scope check failure."""
        report = EvalReport(
            sprint_id="S001",
            overall_status="fail",
            summary="Modified files outside scope",
            commands_run=[],
            criteria=[],
            diff_scope_check=DiffScopeCheck(
                status="fail",
                unexpected_files_modified=["src/unrelated.ts", "lib/extra.ts"]
            ),
            logs=Logs(app_log=None, console_log=None)
        )

        assert report.diff_scope_check.status == "fail"
        assert len(report.diff_scope_check.unexpected_files_modified) == 2
