"""Tests for project bootstrapper."""

from vch.bootstrapper import ProjectBootstrapper


def test_bootstrapper_creates_static_web_app_for_todo_task(tmp_path):
    created = ProjectBootstrapper(str(tmp_path)).maybe_bootstrap("实现一个运行 Todo List 网站")

    assert created is True
    assert (tmp_path / "package.json").exists()
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "src" / "app.js").exists()
    assert (tmp_path / "scripts" / "validate-app.mjs").exists()
    assert (tmp_path / ".harness" / "BOOTSTRAP_REPORT.md").exists()


def test_bootstrapper_does_not_overwrite_existing_app(tmp_path):
    (tmp_path / "package.json").write_text("{}")

    created = ProjectBootstrapper(str(tmp_path)).maybe_bootstrap("实现一个运行 Todo List 网站")

    assert created is False
    assert (tmp_path / "package.json").read_text() == "{}"
