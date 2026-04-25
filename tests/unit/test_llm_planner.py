"""Tests for LLM-backed planner path."""

from openjia.agents.planner import Planner
from openjia.llm import OpenAICompatibleChatBackend, make_llm_backend


class FakeLLMBackend:
    """Fake backend returning a valid feature spec."""

    def generate_json(self, *, instructions, prompt, schema):
        return {
            "project_goal": "Add login",
            "non_goals": [],
            "assumptions": ["fake llm"],
            "features": [
                {
                    "id": "F001",
                    "title": "Login",
                    "user_value": "Users can sign in",
                    "dependencies": [],
                    "risk": "medium",
                    "estimated_files": ["src/login.ts"],
                    "acceptance_criteria": [
                        {
                            "id": "AC001",
                            "description": "Login test passes",
                            "verification_type": "unit",
                            "oracle": "npm test exits 0",
                            "required_evidence": ["command_output"],
                        }
                    ],
                    "definition_of_done": ["EVAL_REPORT passes"],
                }
            ],
            "sprints": [
                {
                    "id": "S001",
                    "goal": "Login",
                    "features": ["F001"],
                    "max_files_to_touch": 2,
                    "must_not_touch": [".git/**"],
                    "verification_commands": ["npm test"],
                    "rollback_strategy": "revert touched files",
                }
            ],
        }


def test_planner_can_use_llm_backend(tmp_path):
    planner = Planner(str(tmp_path), llm_backend=FakeLLMBackend())

    spec = planner.invoke("Add login")

    assert spec.project_goal == "Add login"
    assert spec.assumptions == ["fake llm"]
    assert (tmp_path / ".harness" / "FEATURE_LEDGER.json").exists()


def test_make_minimax_backend(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    backend = make_llm_backend("minimax", "MiniMax-M2.7")

    assert isinstance(backend, OpenAICompatibleChatBackend)
    assert backend.base_url == "https://api.minimaxi.com/v1"
    assert backend.api_key_env == "MINIMAX_API_KEY"
