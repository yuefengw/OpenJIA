"""Integration test for simple bugfix flow."""

import pytest
from pathlib import Path
import tempfile
import shutil


class TestSimpleBugfixFlow:
    """Test a simple bugfix through the full VCH flow."""

    def setup_method(self):
        """Set up test repo."""
        self.repo_dir = Path(tempfile.mkdtemp())

        # Create a minimal Node.js project
        (self.repo_dir / "package.json").write_text("""
{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": {
    "test": "echo 'No tests' && exit 0",
    "build": "echo 'Build done' && exit 0"
  }
}
""")

        self.harness_dir = self.repo_dir / ".harness"

    def teardown_method(self):
        """Clean up test repo."""
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    def test_init_creates_harness_directory(self):
        """Test that init creates the harness directory structure."""
        from vch.agents.initializer import Initializer

        initializer = Initializer(str(self.repo_dir))
        run_state = initializer.invoke("Fix the login bug")

        assert self.harness_dir.exists()
        assert (self.harness_dir / "RUN_STATE.json").exists()
        assert (self.harness_dir / "ENV_REPORT.md").exists()
        assert (self.harness_dir / "REPO_MAP.md").exists()
        assert (self.harness_dir / "RUN.md").exists()
        assert (self.harness_dir / "REQUIREMENTS.md").exists()
        assert (self.harness_dir / "GLOBAL_CONSTRAINTS.md").exists()
        assert (self.harness_dir / "logs" / "commands.jsonl").exists()
        assert (self.harness_dir / "logs" / "tool_calls.jsonl").exists()

    def test_orchestrator_initializes_correctly(self):
        """Test that orchestrator can be created."""
        from vch.orchestrator import HarnessOrchestrator

        orchestrator = HarnessOrchestrator(
            repo_root=str(self.repo_dir),
            max_sprints=2,
            max_repair_attempts=2
        )

        assert orchestrator.max_sprints == 2
        assert orchestrator.max_repair_attempts == 2

    def test_plan_gate_rejects_invalid_spec(self):
        """Test that plan gate rejects invalid specs."""
        from vch.gates.plan_feasibility import PlanFeasibilityGate
        from vch.schemas.feature_spec import FeatureSpec

        gate = PlanFeasibilityGate()

        # Empty spec should not pass feasibility
        spec = FeatureSpec(
            project_goal="",
            features=[],
            sprints=[]
        )

        result = gate.validate(spec)
        assert result.passed is False

    def test_evaluation_gate_handles_pass(self):
        """Test evaluation gate with passing report."""
        from vch.gates.evaluation_gate import EvaluationGate
        from vch.schemas.eval_report import EvalReport, CriterionResult

        gate = EvaluationGate()

        report = EvalReport(
            sprint_id="S001",
            overall_status="pass",
            summary="All good",
            commands_run=[],
            criteria=[],
            diff_scope_check={"status": "pass", "unexpected_files_modified": []},
            logs={"app_log": None, "console_log": None}
        )

        decision = gate.decide(report)
        assert decision.kind.value == "pass"

    def test_context_curator_builds_manifest(self):
        """Test context curator builds manifest."""
        from vch.context.curator import ContextCurator
        from vch.schemas.contract import Contract, Scope

        curator = ContextCurator()

        contract = Contract(
            sprint_id="S001",
            goal="Test sprint",
            scope=Scope(include=["src/**"], exclude=[]),
            allowed_files=["src/**/*.ts"],
            forbidden_files=[],
            acceptance_criteria=[],
            required_commands=["npm test"],
            pass_threshold={},
            repair_policy={"max_repair_attempts": 3}
        )

        manifest = curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(self.repo_dir)
        )

        assert manifest.sprint_id == "S001"
        assert manifest.git_base == "abc123"
