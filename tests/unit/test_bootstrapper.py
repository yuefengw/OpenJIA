"""Tests for project bootstrapper."""

from openjia.bootstrapper import ProjectBootstrapper


def test_bootstrapper_creates_generic_web_runtime_for_web_task(tmp_path):
    created = ProjectBootstrapper(str(tmp_path)).maybe_bootstrap("Build a runnable portfolio website")

    assert created is True
    assert (tmp_path / "package.json").exists()
    assert not (tmp_path / "index.html").exists()
    assert not (tmp_path / "src" / "app.js").exists()
    assert (tmp_path / "scripts" / "validate-app.mjs").exists()
    assert (tmp_path / ".harness" / "BOOTSTRAP_REPORT.md").exists()


def test_bootstrapper_generic_web_scaffold_leaves_app_files_to_generator(tmp_path):
    created = ProjectBootstrapper(str(tmp_path)).maybe_bootstrap(
        "Build a runnable portfolio website",
        mode="generic_web",
    )

    assert created is True
    assert (tmp_path / "package.json").exists()
    assert (tmp_path / "scripts" / "validate-app.mjs").exists()
    assert (tmp_path / "scripts" / "browser-e2e.mjs").exists()
    assert not (tmp_path / "index.html").exists()
    assert not (tmp_path / "src" / "app.js").exists()
    assert "generic_web" in (tmp_path / ".harness" / "BOOTSTRAP_REPORT.md").read_text()


def test_bootstrapper_does_not_overwrite_existing_app(tmp_path):
    (tmp_path / "package.json").write_text("{}")

    created = ProjectBootstrapper(str(tmp_path)).maybe_bootstrap("Build a runnable portfolio website")

    assert created is False
    assert (tmp_path / "package.json").read_text() == "{}"
