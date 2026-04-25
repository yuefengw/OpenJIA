"""Evidence collection for evaluator decisions."""

from pathlib import Path
import json
import subprocess


class EvaluationEvidenceCollector:
    """Collect logs, command records, diffs, and test artifacts for evaluation."""

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def collect(self, sprint_id: str, git_base: str, git_head: str) -> dict:
        """Collect an evaluator evidence packet."""
        sprint_dir = self.repo_root / ".harness" / "sprints" / sprint_id
        evidence = {
            "sprint_id": sprint_id,
            "command_records": self._read_jsonl(self.repo_root / ".harness" / "logs" / "commands.jsonl"),
            "command_logs": self._files_under(sprint_dir / "ARTIFACTS" / "command_outputs"),
            "test_artifacts": self._files_under(self.repo_root / "test-results")
            + self._files_under(self.repo_root / "playwright-report"),
            "git_diff_name_only": self._git(["diff", "--name-only", git_base, git_head]),
            "git_diff_stat": self._git(["diff", "--stat", git_base, git_head]),
            "self_verify_report": self._read_optional(sprint_dir / "SELF_VERIFY_REPORT.md"),
            "changeset": self._read_optional(sprint_dir / "CHANGESET.md"),
        }
        return evidence

    def save(self, evidence: dict, sprint_dir: str) -> str:
        """Persist evidence packet."""
        path = Path(sprint_dir) / "EVIDENCE_PACKET.json"
        path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _files_under(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        return [str(file) for file in path.rglob("*") if file.is_file()]

    def _read_optional(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8", errors="replace")

    def _read_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"unparsed": line})
        return records

    def _git(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as error:
            return f"git unavailable: {error}"
        if result.returncode != 0:
            return result.stderr
        return result.stdout
