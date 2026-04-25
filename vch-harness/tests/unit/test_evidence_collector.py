"""Tests for evaluation evidence collector."""

from vch.evidence import EvaluationEvidenceCollector


def test_evidence_collector_collects_command_logs_and_artifacts(tmp_path):
    command_dir = tmp_path / ".harness" / "sprints" / "S001" / "ARTIFACTS" / "command_outputs"
    command_dir.mkdir(parents=True)
    (command_dir / "npm_test.log").write_text("ok", encoding="utf-8")
    logs_dir = tmp_path / ".harness" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "commands.jsonl").write_text('{"cmd":"npm test","exit_code":0}\n', encoding="utf-8")
    test_results = tmp_path / "test-results"
    test_results.mkdir()
    (test_results / "todo-pass.png").write_text("png", encoding="utf-8")

    evidence = EvaluationEvidenceCollector(str(tmp_path)).collect("S001", "HEAD", "HEAD")

    assert evidence["command_records"][0]["cmd"] == "npm test"
    assert any(path.endswith("npm_test.log") for path in evidence["command_logs"])
    assert any(path.endswith("todo-pass.png") for path in evidence["test_artifacts"])
