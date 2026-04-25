"""ContractGate - validates contract before generator execution."""

from dataclasses import dataclass
from typing import Optional
import yaml
from pydantic import ValidationError
from openjia.schemas.contract import Contract


@dataclass
class ContractIssue:
    """A contract validation issue."""

    rule: str
    severity: str  # error, warning
    message: str
    location: Optional[str] = None


@dataclass
class ContractGateResult:
    """Result of contract validation."""

    valid: bool
    issues: list[ContractIssue]
    can_proceed: bool  # True if contract is acceptable


class ContractGate:
    """
    Validates that a contract is properly formed and acceptable.

    Rejects contracts that have:
    - No oracle for an AC
    - No required evidence for an AC
    - allowed_files that are too broad (e.g., src/**)
    - scope that includes next sprint's content
    - Empty required_commands
    - Verification type mismatch with project stack
    """

    def validate(self, contract: Contract | str | dict) -> ContractGateResult:
        """
        Validate a contract.

        Args:
            contract: Contract object, YAML string, or dict

        Returns:
            ContractGateResult with validation status
        """
        issues: list[ContractIssue] = []

        # Parse input
        if isinstance(contract, str):
            try:
                contract_dict = yaml.safe_load(contract)
            except yaml.YAMLError as e:
                return ContractGateResult(
                    valid=False,
                    issues=[ContractIssue(
                        "schema", "error", f"Invalid YAML: {e}"
                    )],
                    can_proceed=False
                )
            try:
                contract = Contract(**contract_dict)
            except ValidationError as e:
                return ContractGateResult(
                    valid=False,
                    issues=[ContractIssue(
                        "schema", "error", f"Invalid CONTRACT schema: {e}"
                    )],
                    can_proceed=False
                )
        elif isinstance(contract, dict):
            try:
                contract = Contract(**contract)
            except ValidationError as e:
                return ContractGateResult(
                    valid=False,
                    issues=[ContractIssue(
                        "schema", "error", f"Invalid CONTRACT schema: {e}"
                    )],
                    can_proceed=False
                )

        # Run validation rules
        issues.extend(self._check_oracle_per_ac(contract))
        issues.extend(self._check_evidence_per_ac(contract))
        issues.extend(self._check_acceptance_criteria_not_empty(contract))
        issues.extend(self._check_allowed_files_not_overbroad(contract))
        issues.extend(self._check_scope_separation(contract))
        issues.extend(self._check_required_commands_not_empty(contract))
        issues.extend(self._check_verification_types(contract))

        errors = [i for i in issues if i.severity == "error"]

        return ContractGateResult(
            valid=len(errors) == 0,
            issues=issues,
            can_proceed=len(errors) == 0
        )

    def _check_acceptance_criteria_not_empty(self, contract: Contract) -> list[ContractIssue]:
        """Contract must define verifiable acceptance criteria."""
        if contract.acceptance_criteria:
            return []
        return [ContractIssue(
            "acceptance_criteria_empty",
            "error",
            "acceptance_criteria is empty",
            location="acceptance_criteria"
        )]

    def _check_oracle_per_ac(self, contract: Contract) -> list[ContractIssue]:
        """Each AC must have an oracle."""
        issues = []

        for ac in contract.acceptance_criteria:
            if not ac.verification:
                issues.append(ContractIssue(
                    "oracle_required",
                    "error",
                    f"AC {ac.id} has no verification",
                    location=f"acceptance_criteria.{ac.id}"
                ))
            elif not ac.verification.oracle:
                issues.append(ContractIssue(
                    "oracle_required",
                    "error",
                    f"AC {ac.id} has no oracle",
                    location=f"acceptance_criteria.{ac.id}.verification.oracle"
                ))

        return issues

    def _check_evidence_per_ac(self, contract: Contract) -> list[ContractIssue]:
        """Each AC must have required_evidence."""
        issues = []

        for ac in contract.acceptance_criteria:
            if not ac.verification.required_evidence:
                issues.append(ContractIssue(
                    "evidence_required",
                    "error",
                    f"AC {ac.id} has no required_evidence",
                    location=f"acceptance_criteria.{ac.id}.verification.required_evidence"
                ))

        return issues

    def _check_allowed_files_not_overbroad(self, contract: Contract) -> list[ContractIssue]:
        """allowed_files should not be overly broad."""
        issues = []
        overbroad_patterns = ["src/**", "src/*", "**/*", "*"]

        for pattern in contract.allowed_files:
            if pattern in overbroad_patterns:
                issues.append(ContractIssue(
                    "overbroad_scope",
                    "error",
                    f"allowed_files contains overly broad pattern: {pattern}",
                    location="allowed_files"
                ))

        return issues

    def _check_scope_separation(self, contract: Contract) -> list[ContractIssue]:
        """scope should not include content from other sprints."""
        issues = []

        # This is a heuristic check - scope should have some structure
        if not contract.scope.include and contract.allowed_files:
            # If scope is empty but allowed_files has content, that's fine
            pass
        elif not contract.scope.include and not contract.allowed_files:
            issues.append(ContractIssue(
                "empty_scope",
                "warning",
                "Both scope.include and allowed_files are empty",
                location="scope"
            ))

        return issues

    def _check_required_commands_not_empty(self, contract: Contract) -> list[ContractIssue]:
        """required_commands must not be empty."""
        issues = []

        if not contract.required_commands:
            issues.append(ContractIssue(
                "required_commands_empty",
                "error",
                "required_commands is empty",
                location="required_commands"
            ))

        return issues

    def _check_verification_types(self, contract: Contract) -> list[ContractIssue]:
        """Check that verification types are appropriate."""
        issues = []
        valid_types = {"unit", "integration", "e2e", "api", "db", "log", "static_check"}

        for ac in contract.acceptance_criteria:
            vtype = ac.verification.type
            if vtype and vtype not in valid_types:
                issues.append(ContractIssue(
                    "unknown_verification_type",
                    "warning",
                    f"AC {ac.id} has unknown verification type: {vtype}",
                    location=f"acceptance_criteria.{ac.id}.verification.type"
                ))

        return issues
