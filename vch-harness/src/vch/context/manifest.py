"""ContextManifest schema for VCH context management."""

from typing import Optional
from pydantic import BaseModel, Field


class ContextManifest(BaseModel):
    """
    Manifest defining the context for a generator/evaluator invocation.

    This controls what files and information are available to agents
    during a sprint or repair attempt.
    """

    sprint_id: str = Field(..., description="Sprint identifier")
    git_base: str = Field(..., description="Git base commit hash")
    git_head: str = Field(..., description="Git head commit hash")

    must_read: list[str] = Field(
        default_factory=list,
        description="Files that must be read before starting"
    )
    may_read: list[str] = Field(
        default_factory=list,
        description="Files that may be read if needed"
    )
    forbidden_context: list[str] = Field(
        default_factory=list,
        description="Context that should NOT be provided"
    )

    latest_failure: Optional[dict] = Field(
        None,
        description="Information about the latest failure if any"
    )

    allowed_write_paths: list[str] = Field(
        default_factory=list,
        description="Paths that can be written to"
    )

    # Context categories for organization
    stable_context: list[str] = Field(
        default_factory=list,
        description="AGENTS.md, PROJECT_RULES.md, architecture constraints"
    )
    current_task_context: list[str] = Field(
        default_factory=list,
        description="CONTRACT.yaml, current sprint goal, acceptance criteria"
    )
    relevant_code_context: list[str] = Field(
        default_factory=list,
        description="Relevant files, symbols, tests, routes"
    )
    current_failure_context: list[str] = Field(
        default_factory=list,
        description="Failed ACs, minimal reproduction, latest logs"
    )
    state_integrity_context: list[str] = Field(
        default_factory=list,
        description="Git commit, diff stat, allowed/forbidden paths"
    )

    def get_all_must_read(self) -> list[str]:
        """Get all must-read files including categorized ones."""
        all_files = set(self.must_read)
        all_files.update(self.stable_context)
        all_files.update(self.current_task_context)
        all_files.update(self.current_failure_context)
        all_files.update(self.state_integrity_context)
        return list(all_files)

    def get_all_may_read(self) -> list[str]:
        """Get all may-read files."""
        all_files = set(self.may_read)
        all_files.update(self.relevant_code_context)
        return list(all_files)
