"""End-to-end deterministic web app flow."""

from vch.orchestrator import HarnessOrchestrator


def test_run_creates_and_verifies_static_todo_app(tmp_path):
    orchestrator = HarnessOrchestrator(str(tmp_path))

    state = orchestrator.run("实现一个运行 Todo List 网站，支持新增、完成、删除待办，并刷新后保留数据")

    assert state.status == "completed"
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "src" / "app.js").exists()
    assert "localStorage" in (tmp_path / "src" / "app.js").read_text(encoding="utf-8")
    assert (tmp_path / ".harness" / "sprints" / "S001" / "EVAL_REPORT.json").exists()
