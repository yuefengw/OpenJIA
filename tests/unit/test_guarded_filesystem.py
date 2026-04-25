"""Tests for guarded filesystem writes."""

import pytest

from openjia.tools.filesystem import GuardedFilesystem


def test_guarded_filesystem_allows_contract_path(tmp_path):
    fs = GuardedFilesystem(str(tmp_path), ["src/app.js"])

    fs.write_text("src/app.js", "console.log('ok')")

    assert (tmp_path / "src" / "app.js").exists()


def test_guarded_filesystem_rejects_forbidden_path(tmp_path):
    fs = GuardedFilesystem(str(tmp_path), ["src/app.js"])

    with pytest.raises(PermissionError):
        fs.write_text("README.md", "nope")
