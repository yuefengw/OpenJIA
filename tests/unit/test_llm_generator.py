"""Tests for LLM-backed generator path."""

import pytest

from openjia.agents.generator import Generator
from openjia.schemas.contract import Contract, Scope


class FakeGeneratorBackend:
    """Fake backend returning contract-scoped file content."""

    def generate_json(self, *, instructions, prompt, schema):
        return {
            "summary": "write app",
            "files": [
                {
                    "path": "src/app.js",
                    "content": "console.log('generated');\n",
                }
            ],
        }


class BadGeneratorBackend:
    """Fake backend trying to write out of scope."""

    def generate_json(self, *, instructions, prompt, schema):
        return {
            "summary": "bad write",
            "files": [
                {
                    "path": "README.md",
                    "content": "not allowed\n",
                }
            ],
        }


def _contract() -> Contract:
    return Contract(
        sprint_id="S001",
        goal="Generate app file",
        scope=Scope(include=["src/app.js"], exclude=[]),
        allowed_files=["src/app.js"],
        forbidden_files=[],
        acceptance_criteria=[
            {
                "id": "AC001",
                "behavior": "app file exists",
                "verification": {
                    "type": "static_check",
                    "steps": ["python -c \"from pathlib import Path; assert Path('src/app.js').exists()\""],
                    "oracle": ["file exists"],
                    "required_evidence": ["command_output"],
                },
            }
        ],
        required_commands=["python -c \"from pathlib import Path; assert Path('src/app.js').exists()\""],
        pass_threshold={},
        repair_policy={"max_repair_attempts": 3},
    )


def test_llm_generator_writes_allowed_file_and_self_verifies(tmp_path):
    generator = Generator(str(tmp_path), llm_backend=FakeGeneratorBackend())

    result = generator.invoke("S001", _contract())

    assert result["status"] == "implemented"
    assert (tmp_path / "src" / "app.js").read_text(encoding="utf-8") == "console.log('generated');\n"
    assert (tmp_path / ".harness" / "sprints" / "S001" / "SELF_VERIFY_REPORT.md").exists()


def test_llm_generator_out_of_scope_falls_back_without_writing_forbidden_file(tmp_path):
    generator = Generator(str(tmp_path), llm_backend=BadGeneratorBackend())

    generator.invoke("S001", _contract())

    assert not (tmp_path / "README.md").exists()
    assert (tmp_path / ".harness" / "sprints" / "S001" / "GENERATOR_ERROR.md").exists()
