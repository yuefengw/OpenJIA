"""Unit tests for ContractGate."""

import pytest
from openjia.gates.contract_gate import ContractGate
from openjia.schemas.contract import Contract, AcceptanceCriteria, Scope, RepairPolicy


class TestContractGate:
    """Tests for ContractGate."""

    def setup_method(self):
        """Set up test fixtures."""
        self.gate = ContractGate()

    def _make_ac(self, acid: str, **kwargs) -> AcceptanceCriteria:
        """Helper to create an AcceptanceCriteria."""
        defaults = {
            "id": acid,
            "behavior": f"AC {acid} behavior",
            "verification": {"type": "unit"},
            "steps": [],
            "oracle": ["Test passes"],
            "required_evidence": ["test_output"],
        }
        defaults.update(kwargs)
        return AcceptanceCriteria(**defaults)

    def _make_contract(self, **kwargs) -> Contract:
        """Helper to create a Contract."""
        defaults = {
            "sprint_id": "S001",
            "goal": "Test sprint",
            "scope": Scope(include=["src/**"], exclude=[]),
            "allowed_files": ["src/**/*.ts"],
            "forbidden_files": [],
            "acceptance_criteria": [self._make_ac("AC001")],
            "required_commands": ["npm test"],
            "pass_threshold": {"all_acceptance_criteria_must_pass": True},
            "repair_policy": RepairPolicy(),
        }
        defaults.update(kwargs)
        return Contract(**defaults)

    def test_accepts_valid_contract(self):
        """Test that a valid contract passes."""
        contract = self._make_contract()

        result = self.gate.validate(contract)

        assert result.valid is True
        assert result.can_proceed is True
        assert len(result.issues) == 0

    def test_rejects_missing_required_commands(self):
        """Test that empty required_commands is rejected."""
        contract = self._make_contract(required_commands=[])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert result.can_proceed is False
        assert any("required_commands" in i.message.lower() for i in result.issues)

    def test_rejects_invalid_schema_without_throwing(self):
        """Test that malformed dict input returns a gate failure."""
        result = self.gate.validate({"sprint_id": "S001"})

        assert result.valid is False
        assert result.can_proceed is False
        assert any(issue.rule == "schema" for issue in result.issues)

    def test_rejects_overbroad_allowed_files(self):
        """Test that overly broad allowed_files is rejected."""
        contract = self._make_contract(allowed_files=["**/*"])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert any("overly broad" in i.message.lower() for i in result.issues)

    def test_rejects_ac_without_oracle(self):
        """Test that AC without oracle is rejected."""
        ac = self._make_ac("AC001", oracle=[])
        contract = self._make_contract(acceptance_criteria=[ac])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert any("oracle" in i.message.lower() for i in result.issues)

    def test_rejects_ac_without_evidence(self):
        """Test that AC without required_evidence is rejected."""
        ac = self._make_ac("AC001", required_evidence=[])
        contract = self._make_contract(acceptance_criteria=[ac])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert any("evidence" in i.message.lower() for i in result.issues)

    def test_warns_on_empty_scope(self):
        """Test that empty scope produces warning."""
        contract = self._make_contract(
            scope=Scope(include=[], exclude=[]),
            allowed_files=[]
        )

        result = self.gate.validate(contract)

        warnings = [i for i in result.issues if i.severity == "warning"]
        assert any("empty" in w.message.lower() for w in warnings)

    def test_validates_dict_input(self):
        """Test that dict input is validated correctly."""
        contract_dict = {
            "sprint_id": "S001",
            "goal": "Test",
            "scope": {"include": [], "exclude": []},
            "allowed_files": ["src/**/*.ts"],
            "forbidden_files": [],
            "acceptance_criteria": [{
                "id": "AC001",
                "behavior": "test",
                "verification": {"type": "unit"},
                "oracle": ["pass"],
                "required_evidence": ["output"]
            }],
            "required_commands": ["npm test"],
            "pass_threshold": {},
            "repair_policy": {"max_repair_attempts": 3},
        }

        result = self.gate.validate(contract_dict)

        assert result.valid is True

    def test_accepts_spec_nested_verification_shape(self):
        """Test the documented CONTRACT.yaml nested verification schema."""
        contract_dict = {
            "sprint_id": "S001",
            "goal": "Test",
            "scope": {"include": ["src/login.ts"], "exclude": []},
            "allowed_files": ["src/login.ts"],
            "forbidden_files": [],
            "acceptance_criteria": [{
                "id": "AC001",
                "behavior": "login succeeds",
                "verification": {
                    "type": "unit",
                    "steps": ["npm test"],
                    "oracle": ["login test passes"],
                    "required_evidence": ["command_output"]
                }
            }],
            "required_commands": ["npm test"],
            "pass_threshold": {},
            "repair_policy": {"max_repair_attempts": 3},
        }

        result = self.gate.validate(contract_dict)

        assert result.valid is True

    def test_rejects_empty_acceptance_criteria(self):
        """Test that a contract cannot proceed without verifiable criteria."""
        contract = self._make_contract(acceptance_criteria=[])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert any("acceptance_criteria" in i.rule for i in result.issues)

    def test_rejects_src_star_star_pattern(self):
        """Test that src/** pattern is rejected as too broad."""
        contract = self._make_contract(allowed_files=["src/**"])

        result = self.gate.validate(contract)

        assert result.valid is False
        assert any("overly broad" in i.message.lower() for i in result.issues)
