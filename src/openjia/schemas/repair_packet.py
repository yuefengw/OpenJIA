"""RepairPacket schema for OpenJIA repair loop."""

from typing import Optional
from pydantic import BaseModel, Field


class RepairPacket(BaseModel):
    """A repair packet for the Generator."""

    sprint_id: str = Field(..., description="Sprint identifier")
    current_status: str = Field(..., description="Current failure status")
    failed_ac: str = Field(..., description="Failed acceptance criterion")
    must_fix: list[str] = Field(
        default_factory=list, description="What must be fixed"
    )
    must_not_change: list[str] = Field(
        default_factory=list, description="What must NOT be changed"
    )
    evidence: list[str] = Field(default_factory=list, description="Evidence paths")
    likely_files: list[str] = Field(
        default_factory=list, description="Likely files to modify"
    )
    required_commands: list[str] = Field(
        default_factory=list, description="Commands that must pass after fix"
    )
    completion_condition: list[str] = Field(
        default_factory=list, description="Conditions to stop repair"
    )
    repair_attempt: int = Field(default=1, description="Current repair attempt number")
