"""Tests for three-layer prompt loading."""

from vch.prompts.loader import load_role_prompt


def test_load_role_prompt_includes_common_protocol_and_role_methodology():
    prompt = load_role_prompt("generator.md")

    assert "Layer 1: Universal VCH Protocol" in prompt
    assert "Layer 2: Generator Role Methodology" in prompt
    assert "Layer 3: Generator Output Contract" in prompt


def test_all_core_role_prompts_have_three_layers():
    for name, role in [
        ("planner.md", "Planner"),
        ("generator.md", "Generator"),
        ("evaluator.md", "Evaluator"),
    ]:
        prompt = load_role_prompt(name)
        assert "Layer 1: Universal VCH Protocol" in prompt
        assert f"Layer 2: {role} Role Methodology" in prompt
        assert f"Layer 3: {role} Output Contract" in prompt
