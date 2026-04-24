"""VCH: Verifiable Contextual Harness for DeepAgents SDK."""

__version__ = "0.1.0"

from vch.orchestrator import HarnessOrchestrator
from vch.config import Config
from vch.schemas import (
    FeatureSpec,
    Contract,
    EvalReport,
    RunState,
    RepairPacket,
)

__all__ = [
    "HarnessOrchestrator",
    "Config",
    "FeatureSpec",
    "Contract",
    "EvalReport",
    "RunState",
    "RepairPacket",
]
