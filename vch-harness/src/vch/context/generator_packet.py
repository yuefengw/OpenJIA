"""Generator packet builder for clean, bounded implementation context."""

from pathlib import Path
import json

from vch.context.manifest import ContextManifest
from vch.schemas.contract import Contract
from vch.schemas.repair_packet import RepairPacket


class GeneratorPacketBuilder:
    """Build a narrow, auditable packet for generator invocations."""

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def build(
        self,
        contract: Contract,
        manifest: ContextManifest,
        repair_packet: RepairPacket | None = None,
    ) -> dict:
        """Build generator context from contract, manifest, and allowed files only."""
        allowed_file_contents = {}
        for path in contract.allowed_files:
            file_path = self.repo_root / path
            if file_path.exists() and file_path.is_file():
                allowed_file_contents[path] = file_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

        packet = {
            "sprint_id": contract.sprint_id,
            "contract": contract.model_dump(),
            "context_manifest": manifest.model_dump(),
            "allowed_file_contents": allowed_file_contents,
            "must_read": manifest.get_all_must_read(),
            "may_read": manifest.get_all_may_read(),
            "forbidden_context": manifest.forbidden_context,
            "repair_packet": repair_packet.model_dump() if repair_packet else None,
        }
        return packet

    def save(self, packet: dict, sprint_dir: str) -> str:
        """Persist the packet so humans can audit generator context."""
        path = Path(sprint_dir) / "GENERATOR_PACKET.json"
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)
