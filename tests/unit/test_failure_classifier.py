"""Unit tests for EvaluationGate and FailureClassifier."""

import pytest
from openjia.gates.evaluation_gate import EvaluationGate, FailureClassifier, DecisionKind
from openjia.schemas.eval_report import EvalReport, CriterionResult, CommandsRun, DiffScopeCheck, Logs


class TestFailureClassifier:
    """Tests for FailureClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = FailureClassifier()

    def _make_report(self, overall_status: str, criteria: list) -> EvalReport:
        """Helper to create an EvalReport."""
        return EvalReport(
            sprint_id="S001",
            overall_status=overall_status,
            summary=f"Overall: {overall_status}",
            commands_run=[],
            criteria=criteria,
            diff_scope_check={"status": "pass", "unexpected_files_modified": []},
            logs={"app_log": None, "console_log": None}
        )

    def _make_criterion(self, status: str, failure_type: str = None) -> CriterionResult:
        """Helper to create a CriterionResult."""
        return CriterionResult(
            id="AC001",
            status=status,
            failure_type=failure_type,
            evidence=[],
            observed="observed",
            expected="expected",
            likely_location=[],
            minimal_reproduction=[],
            repair_hint=None
        )

    def test_pass_returns_pass(self):
        """Test that pass overall_status returns PASS."""
        report = self._make_report("pass", [self._make_criterion("pass")])

        result = self.classifier.classify(report)

        assert result == DecisionKind.PASS

    def test_infrastructure_failure_classifies_correctly(self):
        """Test that infrastructure_failure is classified correctly."""
        report = self._make_report("infrastructure_failure", [self._make_criterion("blocked")])

        result = self.classifier.classify(report)

        assert result == DecisionKind.ENVIRONMENT_FAILURE

    def test_blocked_classifies_as_plan_impossible(self):
        """Test that blocked status is classified as plan_impossible."""
        report = self._make_report("blocked", [self._make_criterion("blocked")])

        result = self.classifier.classify(report)

        assert result == DecisionKind.PLAN_IMPOSSIBLE

    def test_implementation_bug_classifies_correctly(self):
        """Test that implementation_bug is classified correctly."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "implementation_bug")]
        )

        result = self.classifier.classify(report)

        assert result == DecisionKind.IMPLEMENTATION_BUG

    def test_test_bug_classifies_correctly(self):
        """Test that test_bug is classified correctly."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "test_bug")]
        )

        result = self.classifier.classify(report)

        assert result == DecisionKind.TEST_BUG

    def test_contract_gap_classifies_correctly(self):
        """Test that contract_gap is classified correctly."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "contract_gap")]
        )

        result = self.classifier.classify(report)

        assert result == DecisionKind.CONTRACT_GAP

    def test_unknown_classifies_as_ambiguous(self):
        """Test that unknown failure type is classified as ambiguous."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "unknown")]
        )

        result = self.classifier.classify(report)

        assert result == DecisionKind.AMBIGUOUS

    def test_no_failed_criteria_returns_ambiguous(self):
        """Test that no failed criteria returns ambiguous."""
        report = self._make_report("fail", [])

        result = self.classifier.classify(report)

        assert result == DecisionKind.AMBIGUOUS


class TestEvaluationGate:
    """Tests for EvaluationGate."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gate = EvaluationGate(max_repair_attempts=3)

    def _make_report(self, overall_status: str, criteria: list) -> EvalReport:
        """Helper to create an EvalReport."""
        return EvalReport(
            sprint_id="S001",
            overall_status=overall_status,
            summary=f"Overall: {overall_status}",
            commands_run=[],
            criteria=criteria,
            diff_scope_check={"status": "pass", "unexpected_files_modified": []},
            logs={"app_log": None, "console_log": None}
        )

    def _make_criterion(self, status: str, failure_type: str = None) -> CriterionResult:
        """Helper to create a CriterionResult."""
        return CriterionResult(
            id="AC001",
            status=status,
            failure_type=failure_type,
            evidence=[],
            observed="observed",
            expected="expected",
            likely_location=[],
            minimal_reproduction=[],
            repair_hint=None
        )

    def test_pass_decision(self):
        """Test pass decision."""
        report = self._make_report("pass", [self._make_criterion("pass")])

        decision = self.gate.decide(report)

        assert decision.kind == DecisionKind.PASS
        assert decision.should_retry is False

    def test_environment_failure_decision(self):
        """Test environment failure decision."""
        report = self._make_report("infrastructure_failure", [])

        decision = self.gate.decide(report)

        assert decision.kind == DecisionKind.ENVIRONMENT_FAILURE
        assert decision.should_retry is False

    def test_plan_impossible_decision(self):
        """Test plan impossible decision."""
        report = self._make_report("blocked", [])

        decision = self.gate.decide(report)

        assert decision.kind == DecisionKind.PLAN_IMPOSSIBLE
        assert decision.should_retry is False

    def test_implementation_bug_generates_repair_packet(self):
        """Test that implementation bug generates repair packet."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "implementation_bug")]
        )

        decision = self.gate.decide(report, current_repair_count=0)

        assert decision.kind == DecisionKind.IMPLEMENTATION_BUG
        assert decision.should_retry is True
        assert decision.repair_packet is not None
        assert decision.repair_packet.failed_ac == "AC001"

    def test_max_repair_attempts_blocks(self):
        """Test that exceeding max repair attempts blocks."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "implementation_bug")]
        )

        decision = self.gate.decide(report, current_repair_count=3)

        assert decision.kind == DecisionKind.PLAN_IMPOSSIBLE
        assert decision.should_retry is False

    def test_test_bug_requires_evaluator_correction(self):
        """Test that test bug requires evaluator correction."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "test_bug")]
        )

        decision = self.gate.decide(report)

        assert decision.kind == DecisionKind.TEST_BUG
        assert decision.should_retry is False

    def test_contract_gap_allows_retry(self):
        """Test that contract gap allows retry."""
        report = self._make_report(
            "fail",
            [self._make_criterion("fail", "contract_gap")]
        )

        decision = self.gate.decide(report)

        assert decision.kind == DecisionKind.CONTRACT_GAP
        assert decision.should_retry is True
