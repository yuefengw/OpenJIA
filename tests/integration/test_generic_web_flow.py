"""End-to-end deterministic generic web app flow."""

from openjia.orchestrator import HarnessOrchestrator


def test_run_creates_and_verifies_generic_static_app(tmp_path):
    orchestrator = HarnessOrchestrator(str(tmp_path))

    state = orchestrator.run("Build a runnable portfolio website")

    assert state.status == "completed"
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "src" / "app.js").exists()
    assert "Generated App" in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / ".harness" / "sprints" / "S001" / "EVAL_REPORT.json").exists()
