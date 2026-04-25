import pytest

from openjia.agents.generator import Generator
from openjia.llm import _coerce_agent_json, make_llm_backend
from openjia.schemas.contract import Contract, Scope


class FailingBackend:
    def generate_json(self, *, instructions, prompt, schema):
        raise ValueError("runtime failed")


def test_make_llm_backend_supports_deepagents(monkeypatch):
    monkeypatch.setenv("OPENJIA_DEEPAGENTS_PROVIDER", "minimax")
    backend = make_llm_backend("deepagents", "MiniMax-M2.7")

    assert backend.__class__.__name__ == "DeepAgentsJSONBackend"
    assert backend.model == "MiniMax-M2.7"
    assert backend.provider_name == "minimax"


def test_deepagents_response_coercion_from_structured_response():
    result = _coerce_agent_json({"structured_response": {"ok": True, "provider": "openjia"}})

    assert result == {"ok": True, "provider": "openjia"}


def test_deepagents_generator_does_not_use_deterministic_fallback(tmp_path):
    contract = Contract(
        sprint_id="S001",
        goal="Build a Todo app",
        scope=Scope(include=["index.html"], exclude=[]),
        allowed_files=["index.html"],
        forbidden_files=[],
        acceptance_criteria=[],
        required_commands=[],
    )
    generator = Generator(
        str(tmp_path),
        llm_backend=FailingBackend(),
        llm_backend_name="deepagents",
    )

    with pytest.raises(ValueError, match="runtime failed"):
        generator.invoke("S001", contract, manifest={})

    assert not (tmp_path / "index.html").exists()
    assert (tmp_path / ".harness" / "sprints" / "S001" / "GENERATOR_ERROR.md").exists()


def test_generator_normalizes_deepagents_workspace_paths(tmp_path):
    generator = Generator(str(tmp_path), llm_backend_name="deepagents")

    assert generator._normalize_generated_path("workspace/src/app.js") == "src/app.js"
    assert generator._normalize_generated_path("/workspace/package.json") == "package.json"
