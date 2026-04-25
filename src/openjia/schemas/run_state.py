"""RunState schema for OpenJIA harness state."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SprintState(BaseModel):
    """State of a sprint."""

    id: str = Field(..., description="Sprint identifier")
    status: str = Field(
        default="pending",
        description="pending|in_progress|passed|failed|blocked",
    )
    contract_path: Optional[str] = Field(None, description="Path to contract file")
    eval_report_path: Optional[str] = Field(None, description="Path to eval report")
    repair_count: int = Field(default=0, description="Number of repair attempts")
    passed_acs: list[str] = Field(default_factory=list, description="Passed ACs")
    failed_acs: list[str] = Field(default_factory=list, description="Failed ACs")
    started_at: Optional[str] = Field(None, description="ISO timestamp")
    completed_at: Optional[str] = Field(None, description="ISO timestamp")


class RunState(BaseModel):
    """The overall run state."""

    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(
        default="initialized",
        description="initialized|running|paused|completed|failed",
    )
    current_phase: str = Field(
        default="initializer",
        description="Current phase: initializer|planner|contract|sprint|final_qa",
    )
    current_sprint: Optional[str] = Field(None, description="Current sprint ID")
    max_repair_attempts: int = Field(default=3, description="Max repair attempts")
    started_at: str = Field(..., description="ISO timestamp")
    repo_root: str = Field(..., description="Repository root path")
    git_base_commit: Optional[str] = Field(None, description="Git base commit")
    sprints: list[SprintState] = Field(
        default_factory=list, description="Sprint states"
    )
    last_error: Optional[str] = Field(None, description="Last error message")
    last_updated: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp",
    )
