"""OpenJIA: OpenJIA agent harness for verifiable long-running software development."""

__version__ = "0.1.0"

from openjia.orchestrator import HarnessOrchestrator
from openjia.config import Config
from openjia.schemas import (
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
