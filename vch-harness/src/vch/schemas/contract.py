"""Contract schema for VCH Contract Negotiation."""

from pydantic import BaseModel, Field, model_validator


class VerificationConfig(BaseModel):
    """Verification details for an acceptance criterion."""

    type: str = Field(
        ...,
        description="unit|integration|e2e|api|db|log|static_check",
    )
    steps: list[str] = Field(default_factory=list, description="Verification steps")
    oracle: list[str] = Field(default_factory=list, description="Success conditions")
    required_evidence: list[str] = Field(
        default_factory=list,
        description="Required evidence types: screenshot|trace|log|command_output",
    )


class AcceptanceCriteria(BaseModel):
    """An acceptance criterion in a contract."""

    id: str = Field(..., description="AC identifier")
    behavior: str = Field(..., description="Expected behavior")
    verification: VerificationConfig = Field(..., description="Verification config")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_verification_fields(cls, data):
        """Accept older top-level oracle/evidence fields and move them under verification."""
        if not isinstance(data, dict):
            return data

        verification = dict(data.get("verification") or {})
        for field in ("steps", "oracle", "required_evidence"):
            if field in data and field not in verification:
                verification[field] = data[field]
        data = dict(data)
        data["verification"] = verification
        return data

    @property
    def steps(self) -> list[str]:
        """Backward-compatible access to verification steps."""
        return self.verification.steps

    @property
    def oracle(self) -> list[str]:
        """Backward-compatible access to oracle clauses."""
        return self.verification.oracle

    @property
    def required_evidence(self) -> list[str]:
        """Backward-compatible access to required evidence."""
        return self.verification.required_evidence


class Scope(BaseModel):
    """Contract scope."""

    include: list[str] = Field(default_factory=list, description="Included paths")
    exclude: list[str] = Field(default_factory=list, description="Excluded paths")


class RepairPolicy(BaseModel):
    """Repair policy for the contract."""

    max_repair_attempts: int = Field(default=3, description="Max repair attempts")
    if_same_error_twice: str = Field(
        default="ask_planner_or_change_approach",
        description="Policy when same error repeats",
    )


class Contract(BaseModel):
    """The negotiated contract for a sprint."""

    sprint_id: str = Field(..., description="Sprint identifier")
    goal: str = Field(..., description="Sprint goal")
    scope: Scope = Field(default_factory=Scope, description="Scope definition")
    allowed_files: list[str] = Field(
        default_factory=list, description="Allowed file paths/globs"
    )
    forbidden_files: list[str] = Field(
        default_factory=list, description="Forbidden file paths/globs"
    )
    acceptance_criteria: list[AcceptanceCriteria] = Field(
        default_factory=list, description="Acceptance criteria"
    )
    required_commands: list[str] = Field(
        default_factory=list, description="Commands that must pass"
    )
    pass_threshold: dict = Field(
        default_factory=dict,
        description="Pass threshold configuration",
    )
    repair_policy: RepairPolicy = Field(
        default_factory=RepairPolicy, description="Repair policy"
    )
