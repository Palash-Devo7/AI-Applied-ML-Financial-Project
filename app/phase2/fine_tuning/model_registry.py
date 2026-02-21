"""STUB: Model registry for tracking fine-tuned adapter versions (Phase 2).

Provides versioning, metadata, and A/B testing hooks for LoRA adapters.

Phase 2 implementation options:
- MLflow Model Registry (recommended for enterprise)
- HuggingFace Hub (open-source sharing)
- Simple filesystem registry (minimal viable)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AdapterVersion:
    """Metadata for a registered adapter version."""
    version_id: str
    base_model: str
    adapter_path: str
    training_samples: int
    eval_metrics: dict
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_production: bool = False
    tags: list[str] = field(default_factory=list)


class ModelRegistry:
    """STUB: Track and manage LoRA adapter versions.

    Phase 2 implementation:
    - Register adapters after training
    - Compare eval metrics across versions
    - Promote best version to production
    - Serve via GenerationService.FineTunedModelBackend
    """

    def __init__(self, registry_path: str = "./data/model_registry.json") -> None:
        self.registry_path = registry_path
        raise NotImplementedError("ModelRegistry is a Phase 2 stub.")

    def register(self, version: AdapterVersion) -> str:
        """Register a new adapter version. Returns version_id."""
        raise NotImplementedError

    def get_production_version(self) -> Optional[AdapterVersion]:
        """Return the current production adapter."""
        raise NotImplementedError

    def promote_to_production(self, version_id: str) -> None:
        """Mark a version as the production adapter."""
        raise NotImplementedError

    def list_versions(self) -> list[AdapterVersion]:
        """List all registered adapter versions."""
        raise NotImplementedError

    def compare_versions(self, v1: str, v2: str) -> dict:
        """Compare eval metrics between two versions."""
        raise NotImplementedError
