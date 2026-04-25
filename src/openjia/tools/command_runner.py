"""Command runner that records harness command evidence."""

from pathlib import Path
from datetime import datetime
import json
import subprocess


class CommandRunner:
    """Run shell commands and append `.harness/logs/commands.jsonl` records."""

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def run(self, cmd: str, phase: str, output_dir: Path, timeout: int = 120) -> subprocess.CompletedProcess:
        """Run a command, save output, and append the command ledger."""
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = output_dir / f"{self._cmd_to_name(cmd)}.log"
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=True,
            )
        except subprocess.TimeoutExpired:
            result = subprocess.CompletedProcess(args=cmd, returncode=-1, stdout="", stderr="TIMEOUT")
        except Exception as error:
            result = subprocess.CompletedProcess(args=cmd, returncode=-1, stdout="", stderr=str(error))

        log_path.write_text(
            "\n".join([
                f"Command: {cmd}",
                f"Exit code: {result.returncode}",
                "",
                "--- STDOUT ---",
                result.stdout or "",
                "",
                "--- STDERR ---",
                result.stderr or "",
            ]),
            encoding="utf-8",
            errors="replace",
        )
        self._append_command_record(cmd, phase, result.returncode, log_path)
        return result

    def _append_command_record(self, cmd: str, phase: str, exit_code: int, log_path: Path) -> None:
        logs_dir = self.repo_root / ".harness" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now().isoformat(),
            "phase": phase,
            "cmd": cmd,
            "exit_code": exit_code,
            "log_path": log_path.relative_to(self.repo_root).as_posix()
            if log_path.is_relative_to(self.repo_root)
            else str(log_path),
        }
        with open(logs_dir / "commands.jsonl", "a") as file:
            file.write(json.dumps(record) + "\n")

    def _cmd_to_name(self, cmd: str) -> str:
        import re

        name = re.sub(r"[^a-zA-Z0-9]", "_", cmd)
        return name[:50]
