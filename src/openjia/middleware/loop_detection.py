"""LoopDetectionMiddleware - prevents doom loops."""

from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


@dataclass
class LoopDetectionState:
    """State for loop detection."""

    file_edit_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    command_error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    repair_hint_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    consecutive_failures_without_diff: int = 0
    last_diff: Optional[str] = None


@dataclass
class LoopDetectionResult:
    """Result of loop detection check."""

    is_loop: bool
    loop_type: Optional[str]  # same_file_edits, same_command_error, repair_hint_repeat, no_diff_progress
    message: str
    suggested_action: str


class LoopDetectionMiddleware:
    """
    Middleware to detect and prevent doom loops.

    Detects:
    - Same file edited too many times
    - Same command failing with same error
    - Same repair hint repeated
    - Consecutive failures without meaningful diff changes
    """

    # Thresholds
    MAX_FILE_EDITS = 5
    MAX_SAME_COMMAND_ERRORS = 2
    MAX_REPAIR_HINT_REPEATS = 2
    MAX_CONSECUTIVE_NO_PROGRESS = 3

    def __init__(self):
        self.state = LoopDetectionState()

    def record_file_edit(self, file_path: str) -> None:
        """Record a file edit."""
        self.state.file_edit_counts[file_path] += 1

    def record_command_error(self, command: str, error: str) -> None:
        """Record a command error."""
        key = f"{command}:{error[:100]}"
        self.state.command_error_counts[key] += 1

    def record_repair_hint(self, hint: str) -> None:
        """Record a repair hint."""
        self.state.repair_hint_counts[hint] += 1

    def record_diff(self, diff: str) -> None:
        """Record the current diff."""
        self.state.last_diff = diff

    def check(self) -> LoopDetectionResult:
        """
        Check if we're in a loop.

        Returns:
            LoopDetectionResult with loop status
        """
        # Check file edit count
        for file_path, count in self.state.file_edit_counts.items():
            if count > self.MAX_FILE_EDITS:
                return LoopDetectionResult(
                    is_loop=True,
                    loop_type="same_file_edits",
                    message=f"File '{file_path}' has been edited {count} times",
                    suggested_action="Perform root cause analysis before continuing"
                )

        # Check command error repeat
        for key, count in self.state.command_error_counts.items():
            if count >= self.MAX_SAME_COMMAND_ERRORS:
                return LoopDetectionResult(
                    is_loop=True,
                    loop_type="same_command_error",
                    message=f"Command/error combo repeated {count} times: {key[:100]}",
                    suggested_action="Require different fix approach"
                )

        # Check repair hint repeat
        for hint, count in self.state.repair_hint_counts.items():
            if count >= self.MAX_REPAIR_HINT_REPEATS:
                return LoopDetectionResult(
                    is_loop=True,
                    loop_type="repair_hint_repeat",
                    message=f"Repair hint repeated {count} times: {hint[:100]}",
                    suggested_action="Try alternative fix approach"
                )

        return LoopDetectionResult(
            is_loop=False,
            loop_type=None,
            message="No loop detected",
            suggested_action=""
        )

    def check_no_diff_progress(self, current_diff: str) -> LoopDetectionResult:
        """
        Check if there have been failures without diff changes.

        Args:
            current_diff: Current git diff

        Returns:
            LoopDetectionResult
        """
        if self.state.last_diff == current_diff:
            self.state.consecutive_failures_without_diff += 1

            if self.state.consecutive_failures_without_diff >= self.MAX_CONSECUTIVE_NO_PROGRESS:
                return LoopDetectionResult(
                    is_loop=True,
                    loop_type="no_diff_progress",
                    message=f"No meaningful diff changes for {self.state.consecutive_failures_without_diff} attempts",
                    suggested_action="Stop and require human review"
                )
        else:
            self.state.consecutive_failures_without_diff = 0

        self.state.last_diff = current_diff
        return LoopDetectionResult(
            is_loop=False,
            loop_type=None,
            message="Diff progress OK",
            suggested_action=""
        )

    def reset(self) -> None:
        """Reset loop detection state."""
        self.state = LoopDetectionState()

    def should_pause_and_analyze(self) -> tuple[bool, Optional[str]]:
        """
        Check if we should pause and do deeper analysis.

        Returns:
            Tuple of (should_pause, reason)
        """
        result = self.check()

        if result.is_loop:
            return True, result.message

        return False, None
