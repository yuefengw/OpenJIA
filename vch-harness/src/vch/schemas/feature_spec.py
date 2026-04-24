"""FeatureSpec schema for VCH Planner output."""

from typing import Optional
from pydantic import BaseModel, Field


class AcceptanceCriterion(BaseModel):
    """An acceptance criterion for a feature."""

    id: str = Field(..., description="Unique identifier, e.g., AC001")
    description: str = Field(..., description="Human-readable description")
    verification_type: str = Field(
        ...,
        description="Type: unit|integration|e2e|manual_review|static_check|api|db|log",
    )
    oracle: str = Field(..., description="What defines success for this criterion")
    required_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence types: screenshot, trace, log, test_output",
    )


class Feature(BaseModel):
    """A feature in the feature spec."""

    id: str = Field(..., description="Unique identifier, e.g., F001")
    title: str = Field(..., description="Short title")
    user_value: str = Field(..., description="Why this matters to the user")
    dependencies: list[str] = Field(
        default_factory=list, description="Feature IDs this depends on"
    )
    risk: str = Field(default="medium", description="low|medium|high")
    estimated_files: list[str] = Field(
        default_factory=list, description="Paths of files likely to be modified"
    )
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list, description="Acceptance criteria"
    )
    definition_of_done: list[str] = Field(
        default_factory=list, description="Additional done criteria"
    )


class Sprint(BaseModel):
    """A sprint in the roadmap."""

    id: str = Field(..., description="Unique identifier, e.g., S001")
    goal: str = Field(..., description="Sprint goal")
    features: list[str] = Field(
        default_factory=list, description="Feature IDs included in this sprint"
    )
    max_files_to_touch: int = Field(
        default=6, description="Maximum files to modify"
    )
    must_not_touch: list[str] = Field(
        default_factory=list, description="Globs that should not be modified"
    )
    verification_commands: list[str] = Field(
        default_factory=list, description="Commands to verify the sprint"
    )
    rollback_strategy: Optional[str] = Field(
        None, description="How to rollback if this sprint fails"
    )


class FeatureSpec(BaseModel):
    """The output of the Planner agent."""

    project_goal: str = Field(..., description="Overall project goal")
    non_goals: list[str] = Field(
        default_factory=list, description="What this project will NOT do"
    )
    assumptions: list[str] = Field(
        default_factory=list, description="Assumptions made"
    )
    features: list[Feature] = Field(
        default_factory=list, description="All features"
    )
    sprints: list[Sprint] = Field(
        default_factory=list, description="Sprint roadmap"
    )
