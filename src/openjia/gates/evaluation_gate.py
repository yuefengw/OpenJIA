"""EvaluationGate - decides what to do based on eval report."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from openjia.schemas.eval_report import EvalReport
from openjia.schemas.repair_packet import RepairPacket


class DecisionKind(Enum):
    """Types of evaluation decisions."""

    PASS = "pass"
    IMPLEMENTATION_BUG = "implementation_bug"
    TEST_BUG = "test_bug"
    CONTRACT_GAP = "contract_gap"
    PLAN_IMPOSSIBLE = "plan_impossible"
    ENVIRONMENT_FAILURE = "environment_failure"
    AMBIGUOUS = "ambiguous"


@dataclass
class EvaluationDecision:
    """Decision from the evaluation gate."""

    kind: DecisionKind
    message: str
    repair_packet: Optional[RepairPacket] = None
    should_retry: bool = False
    max_retries: int = 3


class FailureClassifier:
    """
    Classifies failures from eval report into categories.
    """

    @staticmethod
    def classify(eval_report: EvalReport) -> DecisionKind:
        """
        Classify the overall evaluation failure.

        Returns:
            DecisionKind for the primary failure type
        """
        if eval_report.overall_status == "pass":
            return DecisionKind.PASS

        if eval_report.overall_status == "infrastructure_failure":
            return DecisionKind.ENVIRONMENT_FAILURE

        if eval_report.overall_status == "blocked":
            return DecisionKind.PLAN_IMPOSSIBLE

        # Analyze criteria results
        failed_criteria = [c for c in eval_report.criteria if c.status == "fail"]

        if not failed_criteria:
            return DecisionKind.AMBIGUOUS

        # Count failure types
        failure_types: dict[str, int] = {}
        for criterion in failed_criteria:
            ft = criterion.failure_type or "unknown"
            failure_types[ft] = failure_types.get(ft, 0) + 1

        # Primary failure type is the most common
        primary = max(failure_types, key=failure_types.get)

        if primary == "implementation_bug":
            return DecisionKind.IMPLEMENTATION_BUG
        elif primary == "test_bug":
            return DecisionKind.TEST_BUG
        elif primary == "contract_gap":
            return DecisionKind.CONTRACT_GAP
        elif primary == "environment_failure":
            return DecisionKind.ENVIRONMENT_FAILURE
        else:
            return DecisionKind.AMBIGUOUS


class EvaluationGate:
    """
    Decides what action to take based on evaluation report.

    Decisions:
    - pass: commit and proceed to next sprint
    - implementation_bug: generate repair packet and retry
    - test_bug: correct evaluator or escalate
    - contract_gap: renegotiate contract
    - plan_impossible: re-scope with planner
    - environment_failure: re-initialize environment
    - ambiguous: escalate to QA or human
    """

    def __init__(self, max_repair_attempts: int = 3):
        self.max_repair_attempts = max_repair_attempts

    def decide(
        self,
        eval_report: EvalReport,
        current_repair_count: int = 0,
    ) -> EvaluationDecision:
        """
        Make a decision based on the evaluation report.

        Args:
            eval_report: The evaluation report
            current_repair_count: Number of repair attempts so far

        Returns:
            EvaluationDecision with action to take
        """
        kind = FailureClassifier.classify(eval_report)

        if kind == DecisionKind.PASS:
            return EvaluationDecision(
                kind=DecisionKind.PASS,
                message="All acceptance criteria passed",
                should_retry=False
            )

        if kind == DecisionKind.ENVIRONMENT_FAILURE:
            return EvaluationDecision(
                kind=DecisionKind.ENVIRONMENT_FAILURE,
                message="Environment failure detected - needs re-initialization",
                should_retry=False
            )

        if kind == DecisionKind.PLAN_IMPOSSIBLE:
            return EvaluationDecision(
                kind=DecisionKind.PLAN_IMPOSSIBLE,
                message="Sprint is blocked - needs re-planning",
                should_retry=False
            )

        if kind == DecisionKind.AMBIGUOUS:
            return EvaluationDecision(
                kind=DecisionKind.AMBIGUOUS,
                message="Evaluation is ambiguous - needs human review",
                should_retry=False
            )

        if kind == DecisionKind.TEST_BUG:
            return EvaluationDecision(
                kind=DecisionKind.TEST_BUG,
                message="Test or oracle is incorrect - needs evaluator correction",
                should_retry=False
            )

        if kind == DecisionKind.CONTRACT_GAP:
            return EvaluationDecision(
                kind=DecisionKind.CONTRACT_GAP,
                message="Contract is incomplete or涓嶅彲娴?- needs renegotiation",
                should_retry=True
            )

        if kind == DecisionKind.IMPLEMENTATION_BUG:
            # Check if we should retry
            if current_repair_count >= self.max_repair_attempts:
                return EvaluationDecision(
                    kind=DecisionKind.PLAN_IMPOSSIBLE,
                    message=f"Max repair attempts ({self.max_repair_attempts}) exceeded - sprint blocked",
                    should_retry=False
                )

            # Generate repair packet
            repair_packet = self._generate_repair_packet(eval_report, current_repair_count)

            # Check for same error twice
            same_error_twice = self._check_same_error_repeated(eval_report, current_repair_count)

            if same_error_twice:
                return EvaluationDecision(
                    kind=DecisionKind.IMPLEMENTATION_BUG,
                    message="Same error failed twice - requires root cause analysis",
                    repair_packet=repair_packet,
                    should_retry=True
                )

            return EvaluationDecision(
                kind=DecisionKind.IMPLEMENTATION_BUG,
                message=f"Implementation bug - generating repair packet (attempt {current_repair_count + 1})",
                repair_packet=repair_packet,
                should_retry=True
            )

        return EvaluationDecision(
            kind=DecisionKind.AMBIGUOUS,
            message="Could not determine failure type",
            should_retry=False
        )

    def _generate_repair_packet(
        self,
        eval_report: EvalReport,
        current_repair_count: int
    ) -> RepairPacket:
        """Generate a repair packet from the eval report."""
        failed_criteria = [c for c in eval_report.criteria if c.status == "fail"]

        # Collect evidence
        evidence: list[str] = []
        for criterion in failed_criteria:
            evidence.extend(criterion.evidence)

        # Collect likely files
        likely_files: list[str] = []
        for criterion in failed_criteria:
            likely_files.extend(criterion.likely_location)

        # Collect required commands
        required_commands: list[str] = [c.cmd for c in eval_report.commands_run]

        return RepairPacket(
            sprint_id=eval_report.sprint_id,
            current_status=f"Failed: {', '.join([c.id for c in failed_criteria])}",
            failed_ac=failed_criteria[0].id if failed_criteria else "unknown",
            must_fix=[c.observed for c in failed_criteria],
            must_not_change=[],  # Would need contract info
            evidence=evidence,
            likely_files=list(set(likely_files)),
            required_commands=required_commands,
            completion_condition=[
                f"{failed_criteria[0].id} must pass",
                "Previously passing ACs must still pass",
                "REPAIR_REPORT.md must be written"
            ],
            repair_attempt=current_repair_count + 1
        )

    def _check_same_error_repeated(
        self,
        eval_report: EvalReport,
        current_repair_count: int
    ) -> bool:
        """Check if the same error has failed multiple times."""
        # This would need access to previous eval reports
        # For now, return False
        return False
