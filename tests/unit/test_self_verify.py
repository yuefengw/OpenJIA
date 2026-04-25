"""Unit tests for SelfVerifyGate."""

from openjia.gates.self_verify import SelfVerifyGate


def test_self_verify_rejects_todo_exit_code_and_missing_log(tmp_path):
    """Generator placeholders must not satisfy the self-verify gate."""
    sprint_dir = tmp_path / "S001"
    sprint_dir.mkdir()
    (sprint_dir / "CHANGESET.md").write_text("# Changeset\n")
    (sprint_dir / "SELF_VERIFY_REPORT.md").write_text(
        "# Self Verify\n\n"
        "## Commands Run\n"
        "- cmd: npm test\n"
        "  exit_code: [TODO]\n"
        "  log: ARTIFACTS/command_outputs/npm_test.log\n"
    )

    result = SelfVerifyGate().validate(
        required_commands=["npm test"],
        sprint_dir=str(sprint_dir),
    )

    assert result.passed is False
    assert any(issue.rule == "command_exit_code" for issue in result.issues)
    assert any(issue.rule == "command_log" for issue in result.issues)


def test_self_verify_accepts_successful_command_with_existing_log(tmp_path):
    """A command with exit code 0 and a saved log can pass the gate."""
    sprint_dir = tmp_path / "S001"
    log_dir = sprint_dir / "ARTIFACTS" / "command_outputs"
    log_dir.mkdir(parents=True)
    (sprint_dir / "CHANGESET.md").write_text("# Changeset\n")
    (log_dir / "npm_test.log").write_text("ok\n")
    (sprint_dir / "SELF_VERIFY_REPORT.md").write_text(
        "# Self Verify\n\n"
        "## Commands Run\n"
        "- cmd: npm test\n"
        "  exit_code: 0\n"
        "  log: ARTIFACTS/command_outputs/npm_test.log\n"
    )

    result = SelfVerifyGate().validate(
        required_commands=["npm test"],
        sprint_dir=str(sprint_dir),
    )

    assert result.passed is True
    assert result.commands_run == ["npm test"]
