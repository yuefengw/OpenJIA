"""EvalReport schema for VCH Evaluator output."""

from typing import Optional
from pydantic import BaseModel, Field


class CommandsRun(BaseModel):
    """A command that was run."""

    cmd: str = Field(..., description="Command that was executed")
    exit_code: int = Field(..., description="Exit code")
    log_path: Optional[str] = Field(None, description="Path to log file")


class CriterionResult(BaseModel):
    """Result of a single acceptance criterion."""

    id: str = Field(..., description="AC identifier")
    status: str = Field(..., description="pass|fail|blocked")
    failure_type: Optional[str] = Field(
        None,
        description="implementation_bug|test_bug|contract_gap|environment_failure|unknown",
    )
    evidence: list[str] = Field(default_factory=list, description="Evidence paths")
    observed: str = Field(..., description="What was observed")
    expected: str = Field(..., description="What was expected")
    likely_location: list[str] = Field(
        default_factory=list, description="Likely file locations"
    )
    minimal_reproduction: list[str] = Field(
        default_factory=list, description="Minimal reproduction steps"
    )
    repair_hint: Optional[str] = Field(None, description="Hint for fixing")


class DiffScopeCheck(BaseModel):
    """Check of modified files against contract scope."""

    status: str = Field(..., description="pass|fail")
    unexpected_files_modified: list[str] = Field(
        default_factory=list, description="Files modified outside scope"
    )


class Logs(BaseModel):
    """Log file paths."""

    app_log: Optional[str] = Field(None, description="Application log path")
    console_log: Optional[str] = Field(None, description="Console log path")


class EvalReport(BaseModel):
    """The evaluation report from the Evaluator agent."""

    sprint_id: str = Field(..., description="Sprint identifier")
    overall_status: str = Field(
        ...,
        description="pass|fail|blocked|infrastructure_failure",
    )
    summary: str = Field(..., description="Summary of evaluation")
    commands_run: list[CommandsRun] = Field(
        default_factory=list, description="Commands that were run"
    )
    criteria: list[CriterionResult] = Field(
        default_factory=list, description="Per-criterion results"
    )
    diff_scope_check: DiffScopeCheck = Field(
        default_factory=DiffScopeCheck, description="Scope check result"
    )
    logs: Logs = Field(default_factory=Logs, description="Log file references")
