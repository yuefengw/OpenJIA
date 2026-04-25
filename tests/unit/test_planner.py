"""Tests for deterministic planner fallback."""

from openjia.agents.planner import Planner
from openjia.gates.plan_feasibility import PlanFeasibilityGate


def test_deterministic_planner_generates_gate_passing_spec(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"echo ok"}}'
    )
    planner = Planner(str(tmp_path))

    spec = planner.invoke("Add persistent todo items")
    result = PlanFeasibilityGate().validate(spec)

    assert spec.features
    assert spec.sprints
    assert spec.features[0].acceptance_criteria
    assert result.passed is True
    assert (tmp_path / ".harness" / "FEATURE_SPEC.json").exists()
    assert (tmp_path / ".harness" / "FEATURE_LEDGER.json").exists()
