"""End-to-end deterministic web app flow."""

from openjia.orchestrator import HarnessOrchestrator


def test_run_creates_and_verifies_static_todo_app(tmp_path):
    orchestrator = HarnessOrchestrator(str(tmp_path))

    state = orchestrator.run(
        "Build a runnable Todo List website with add, complete, delete, and persistence after refresh"
    )

    assert state.status == "completed"
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "src" / "app.js").exists()
    assert "localStorage" in (tmp_path / "src" / "app.js").read_text(encoding="utf-8")
    assert (tmp_path / ".harness" / "sprints" / "S001" / "EVAL_REPORT.json").exists()
