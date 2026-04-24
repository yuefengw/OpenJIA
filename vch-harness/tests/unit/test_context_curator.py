"""Unit tests for ContextCurator."""

import pytest
from pathlib import Path
from vch.context.curator import ContextCurator
from vch.context.manifest import ContextManifest
from vch.schemas.contract import Contract, Scope


class TestContextCurator:
    """Tests for ContextCurator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.curator = ContextCurator()

    def _make_contract(self, **kwargs) -> Contract:
        """Helper to create a Contract."""
        from vch.schemas.contract import AcceptanceCriteria, RepairPolicy

        defaults = {
            "sprint_id": "S001",
            "goal": "Test sprint",
            "scope": Scope(include=["src/**"], exclude=[]),
            "allowed_files": ["src/**/*.ts", "tests/**/*.ts"],
            "forbidden_files": [],
            "acceptance_criteria": [],
            "required_commands": ["npm test"],
            "pass_threshold": {},
            "repair_policy": RepairPolicy(),
        }
        defaults.update(kwargs)
        return Contract(**defaults)

    def test_build_manifest_basic(self, tmp_path):
        """Test basic manifest building."""
        contract = self._make_contract()

        manifest = self.curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(tmp_path)
        )

        assert manifest.sprint_id == "S001"
        assert manifest.git_base == "abc123"
        assert manifest.git_head == "def456"

    def test_manifest_includes_contract(self, tmp_path):
        """Test that manifest includes contract path in must_read."""
        contract = self._make_contract()

        manifest = self.curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(tmp_path)
        )

        must_read_paths = manifest.get_all_must_read()
        assert any("CONTRACT.yaml" in p for p in must_read_paths)

    def test_manifest_includes_failure_context_when_failed(self, tmp_path):
        """Test that manifest includes failure context when eval failed."""
        from vch.schemas.eval_report import EvalReport, CriterionResult

        contract = self._make_contract()

        eval_report = EvalReport(
            sprint_id="S001",
            overall_status="fail",
            summary="Failed",
            commands_run=[],
            criteria=[
                CriterionResult(
                    id="AC001",
                    status="fail",
                    failure_type="implementation_bug",
                    evidence=["ARTIFACTS/error.log"],
                    observed="Error occurred",
                    expected="No error",
                    likely_location=["src/app.ts"],
                    minimal_reproduction=[],
                    repair_hint="Fix the bug"
                )
            ],
            diff_scope_check={"status": "pass", "unexpected_files_modified": []},
            logs={"app_log": None, "console_log": None}
        )

        manifest = self.curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(tmp_path),
            eval_report=eval_report
        )

        assert manifest.latest_failure is not None
        assert "AC001" in manifest.latest_failure["failed_criteria"]

    def test_manifest_forbidden_context(self, tmp_path):
        """Test that manifest includes forbidden context."""
        contract = self._make_contract()

        manifest = self.curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(tmp_path)
        )

        assert "obsolete eval reports" in manifest.forbidden_context
        assert "old unrelated logs" in manifest.forbidden_context

    def test_save_manifest(self, tmp_path):
        """Test saving manifest to file."""
        contract = self._make_contract()

        manifest = self.curator.build_manifest(
            sprint_id="S001",
            contract=contract,
            git_base="abc123",
            git_head="def456",
            repo_root=str(tmp_path)
        )

        sprint_dir = tmp_path / "sprints" / "S001"
        path = self.curator.save_manifest(manifest, str(sprint_dir))

        assert Path(path).exists()

        # Verify it can be loaded
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["sprint_id"] == "S001"


class TestContextManifest:
    """Tests for ContextManifest."""

    def test_get_all_must_read_includes_categories(self):
        """Test that get_all_must_read includes categorized contexts."""
        manifest = ContextManifest(
            sprint_id="S001",
            git_base="abc",
            git_head="def",
            must_read=["file1.txt"],
            stable_context=["AGENTS.md"],
            current_task_context=["CONTRACT.yaml"],
            current_failure_context=["error.log"],
            state_integrity_context=["git_state.txt"]
        )

        all_must_read = manifest.get_all_must_read()

        assert "file1.txt" in all_must_read
        assert "AGENTS.md" in all_must_read
        assert "CONTRACT.yaml" in all_must_read
        assert "error.log" in all_must_read
        assert "git_state.txt" in all_must_read

    def test_get_all_may_read_includes_categories(self):
        """Test that get_all_may_read includes relevant code context."""
        manifest = ContextManifest(
            sprint_id="S001",
            git_base="abc",
            git_head="def",
            may_read=["file1.txt"],
            relevant_code_context=["src/app.ts"]
        )

        all_may_read = manifest.get_all_may_read()

        assert "file1.txt" in all_may_read
        assert "src/app.ts" in all_may_read
