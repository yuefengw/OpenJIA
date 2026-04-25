"""Tests for generator packet builder."""

from vch.context.generator_packet import GeneratorPacketBuilder
from vch.context.manifest import ContextManifest
from vch.schemas.contract import Contract, Scope


def test_generator_packet_includes_only_allowed_file_contents(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("allowed", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    contract = Contract(
        sprint_id="S001",
        goal="Test",
        scope=Scope(include=["src/app.js"], exclude=[]),
        allowed_files=["src/app.js"],
        forbidden_files=["secret.txt"],
        acceptance_criteria=[
            {
                "id": "AC001",
                "behavior": "works",
                "verification": {
                    "type": "static_check",
                    "steps": ["node --version"],
                    "oracle": ["ok"],
                    "required_evidence": ["command_output"],
                },
            }
        ],
        required_commands=["node --version"],
        pass_threshold={},
        repair_policy={"max_repair_attempts": 3},
    )
    manifest = ContextManifest(
        sprint_id="S001",
        git_base="base",
        git_head="head",
        must_read=[".harness/sprints/S001/CONTRACT.yaml"],
        allowed_write_paths=["src/app.js"],
    )

    packet = GeneratorPacketBuilder(str(tmp_path)).build(contract, manifest)

    assert packet["allowed_file_contents"] == {"src/app.js": "allowed"}
    assert "secret.txt" in packet["contract"]["forbidden_files"]
    assert "secret" not in packet["allowed_file_contents"].values()
