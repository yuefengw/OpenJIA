"""Unit tests for PlanFeasibilityGate."""

import pytest
from openjia.gates.plan_feasibility import PlanFeasibilityGate
from openjia.schemas.feature_spec import FeatureSpec, Feature, AcceptanceCriterion, Sprint


class TestPlanFeasibilityGate:
    """Tests for PlanFeasibilityGate."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gate = PlanFeasibilityGate()

    def _make_spec(self, **kwargs) -> FeatureSpec:
        """Helper to create a FeatureSpec."""
        defaults = {
            "project_goal": "Test project",
            "non_goals": [],
            "assumptions": [],
            "features": [],
            "sprints": [],
        }
        defaults.update(kwargs)
        return FeatureSpec(**defaults)

    def _make_feature(self, fid: str, **kwargs) -> Feature:
        """Helper to create a Feature."""
        defaults = {
            "id": fid,
            "title": f"Feature {fid}",
            "user_value": "Test value",
            "dependencies": [],
            "risk": "medium",
            "estimated_files": [],
            "acceptance_criteria": [],
            "definition_of_done": [],
        }
        defaults.update(kwargs)
        return Feature(**defaults)

    def _make_ac(self, acid: str, **kwargs) -> AcceptanceCriterion:
        """Helper to create an AcceptanceCriterion."""
        defaults = {
            "id": acid,
            "description": f"AC {acid}",
            "verification_type": "unit",
            "oracle": "Test passes",
            "required_evidence": ["test_output"],
        }
        defaults.update(kwargs)
        return AcceptanceCriterion(**defaults)

    def _make_sprint(self, sid: str, features: list[str] = None, **kwargs) -> Sprint:
        """Helper to create a Sprint."""
        defaults = {
            "id": sid,
            "goal": f"Sprint {sid}",
            "features": features or [],
            "max_files_to_touch": 6,
            "must_not_touch": [],
            "verification_commands": ["npm test"],
            "rollback_strategy": None,
        }
        defaults.update(kwargs)
        return Sprint(**defaults)

    def test_accepts_valid_plan(self):
        """Test that a valid plan passes."""
        feature = self._make_feature("F001", acceptance_criteria=[
            self._make_ac("AC001")
        ])
        sprint = self._make_sprint("S001", features=["F001"])

        spec = self._make_spec(
            features=[feature],
            sprints=[sprint]
        )

        result = self.gate.validate(spec)

        assert result.passed is True
        assert result.score >= 0.8
        assert result.recommendation == "pass"

    def test_rejects_missing_oracle(self):
        """Test that missing oracle is rejected."""
        feature = self._make_feature("F001", acceptance_criteria=[
            self._make_ac("AC001", oracle="")
        ])
        sprint = self._make_sprint("S001", features=["F001"])

        spec = self._make_spec(
            features=[feature],
            sprints=[sprint]
        )

        result = self.gate.validate(spec)

        assert result.passed is False
        assert any("oracle" in i.message.lower() for i in result.issues if i.severity == "error")

    def test_rejects_missing_evidence(self):
        """Test that missing required_evidence is rejected."""
        feature = self._make_feature("F001", acceptance_criteria=[
            self._make_ac("AC001", required_evidence=[])
        ])
        sprint = self._make_sprint("S001", features=["F001"])

        spec = self._make_spec(
            features=[feature],
            sprints=[sprint]
        )

        result = self.gate.validate(spec)

        assert result.passed is False
        assert any("evidence" in i.message.lower() for i in result.issues if i.severity == "error")

    def test_rejects_too_large_sprint(self):
        """Test that sprint exceeding max_files_to_touch is rejected."""
        feature = self._make_feature("F001")
        sprint = self._make_sprint("S001", features=["F001"], max_files_to_touch=20)

        spec = self._make_spec(
            features=[feature],
            sprints=[sprint]
        )

        result = self.gate.validate(spec)

        assert result.passed is False
        assert any("max_files" in i.message.lower() or "atomicity" in i.category.lower()
                   for i in result.issues if i.severity == "error")

    def test_detects_dependency_cycle(self):
        """Test that circular dependencies are detected."""
        f1 = self._make_feature("F001", dependencies=["F002"])
        f2 = self._make_feature("F002", dependencies=["F001"])

        spec = self._make_spec(
            features=[f1, f2],
            sprints=[self._make_sprint("S001", features=["F001", "F002"])]
        )

        result = self.gate.validate(spec)

        assert result.passed is False
        assert any("circular" in i.message.lower() for i in result.issues)

    def test_rejects_invalid_json(self):
        """Test that invalid JSON is rejected."""
        result = self.gate.validate("{ invalid json }")

        assert result.passed is False
        assert result.score == 0.0
        assert result.recommendation == "fail"

    def test_rejects_invalid_schema_without_throwing(self):
        """Test that malformed dict input returns a gate failure."""
        result = self.gate.validate({"features": [], "sprints": []})

        assert result.passed is False
        assert result.score == 0.0
        assert result.recommendation == "fail"
        assert any(issue.category == "schema" for issue in result.issues)

    def test_rejects_unknown_feature_reference(self):
        """Test that unknown feature references are caught."""
        sprint = self._make_sprint("S001", features=["F999"])

        spec = self._make_spec(sprints=[sprint])

        result = self.gate.validate(spec)

        assert result.passed is False
        assert any("unknown feature" in i.message.lower() for i in result.issues)

    def test_high_risk_sprint_warns_without_rollback(self):
        """Test that high risk without rollback produces warning."""
        feature = self._make_feature("F001", risk="high")
        sprint = self._make_sprint("S001", features=["F001"], rollback_strategy=None)

        spec = self._make_spec(
            features=[feature],
            sprints=[sprint]
        )

        result = self.gate.validate(spec)

        # Should pass but with warning
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert any("rollback" in w.message.lower() for w in warnings)

    def test_multiple_features_per_sprint(self):
        """Test that multiple features per sprint work when under limit."""
        features = [
            self._make_feature(f"F00{i}", acceptance_criteria=[self._make_ac(f"AC00{i}")])
            for i in range(1, 4)
        ]
        sprint = self._make_sprint("S001", features=["F001", "F002", "F003"])

        spec = self._make_spec(features=features, sprints=[sprint])

        result = self.gate.validate(spec)

        assert result.passed is True
