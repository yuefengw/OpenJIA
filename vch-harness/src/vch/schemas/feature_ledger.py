"""Feature ledger schema for durable harness progress tracking."""

from pydantic import BaseModel, Field


class LedgerAcceptanceCriterion(BaseModel):
    """Durable state for one acceptance criterion."""

    id: str
    description: str
    status: str = Field(default="pending", description="pending|pass|fail|blocked")
    verification_type: str
    oracle: str
    required_evidence: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    latest_failure: str | None = None


class LedgerFeature(BaseModel):
    """Durable state for one feature."""

    id: str
    title: str
    sprint_id: str | None = None
    status: str = Field(default="pending", description="pending|in_progress|pass|fail|blocked")
    acceptance_criteria: list[LedgerAcceptanceCriterion] = Field(default_factory=list)


class FeatureLedger(BaseModel):
    """Run-level feature and acceptance-criteria state."""

    project_goal: str
    features: list[LedgerFeature] = Field(default_factory=list)

    def feature_for_ac(self, ac_id: str) -> LedgerFeature | None:
        """Return the feature containing an AC."""
        for feature in self.features:
            if any(ac.id == ac_id for ac in feature.acceptance_criteria):
                return feature
        return None
