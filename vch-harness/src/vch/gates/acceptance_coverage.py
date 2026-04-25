"""Acceptance coverage gate for evaluator reports."""

from dataclasses import dataclass

from vch.schemas.contract import Contract
from vch.schemas.eval_report import EvalReport


@dataclass
class CoverageIssue:
    """A coverage issue blocking pass."""

    rule: str
    message: str


@dataclass
class CoverageResult:
    """Acceptance coverage result."""

    passed: bool
    issues: list[CoverageIssue]


class AcceptanceCoverageGate:
    """Ensure every contract AC has passing status and concrete evidence."""

    def validate(self, contract: Contract, eval_report: EvalReport) -> CoverageResult:
        issues: list[CoverageIssue] = []
        results_by_id = {criterion.id: criterion for criterion in eval_report.criteria}

        for ac in contract.acceptance_criteria:
            result = results_by_id.get(ac.id)
            if result is None:
                issues.append(CoverageIssue("missing_ac_result", f"Missing eval result for {ac.id}"))
                continue
            if result.status != "pass":
                issues.append(CoverageIssue("ac_not_passed", f"{ac.id} status is {result.status}"))
            if not result.evidence:
                issues.append(CoverageIssue("missing_evidence", f"{ac.id} has no evidence"))
            if not result.observed or "TODO" in result.observed:
                issues.append(CoverageIssue("missing_observation", f"{ac.id} has no concrete observation"))

        if eval_report.diff_scope_check.status != "pass":
            issues.append(CoverageIssue("diff_scope_failed", "Diff scope check failed"))

        for command in eval_report.commands_run:
            if command.exit_code != 0:
                issues.append(CoverageIssue("command_failed", f"{command.cmd} exited {command.exit_code}"))
            if not command.log_path:
                issues.append(CoverageIssue("missing_command_log", f"{command.cmd} has no log path"))

        if eval_report.overall_status == "pass" and issues:
            issues.append(CoverageIssue("false_pass", "Eval report claimed pass but coverage checks failed"))

        return CoverageResult(passed=not issues, issues=issues)
