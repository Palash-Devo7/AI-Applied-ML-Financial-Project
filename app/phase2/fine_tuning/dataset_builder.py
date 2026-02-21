"""STUB: Training dataset builder for LoRA fine-tuning (Phase 2).

Reads JSONL records logged by GenerationService (COLLECT_TRAINING_DATA=true)
and transforms them into instruction-tuning format suitable for SFTTrainer.

Dataset format (input JSONL):
    {"question": str, "context": str, "answer": str}

Output format (Alpaca/instruction-tuning):
    {"instruction": str, "input": str, "output": str}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DatasetConfig:
    """Configuration for dataset preparation."""
    raw_data_path: str = "./data/training_data.jsonl"
    output_dir: str = "./data/datasets"
    train_split: float = 0.9
    min_answer_length: int = 50
    max_samples: Optional[int] = None
    dedup_threshold: float = 0.85


class FinanceDatasetBuilder:
    """STUB: Build and validate training datasets from collected QA pairs.

    Phase 2 implementation:
    - Filter low-quality examples (short answers, hallucinated citations)
    - Deduplicate using MinHash LSH
    - Format for Alpaca / ChatML instruction tuning
    - Split into train/eval sets
    - Push to HuggingFace Hub or save locally
    """

    def __init__(self, config: DatasetConfig) -> None:
        self.config = config
        raise NotImplementedError("DatasetBuilder is a Phase 2 stub.")

    def load_raw_data(self) -> list[dict]:
        """Load JSONL records from GenerationService logging."""
        raise NotImplementedError

    def filter_and_clean(self, records: list[dict]) -> list[dict]:
        """Remove low-quality, duplicate, and malformed records."""
        raise NotImplementedError

    def format_for_training(self, records: list[dict]) -> list[dict]:
        """Convert to instruction-tuning format."""
        raise NotImplementedError

    def split_and_save(self, formatted: list[dict]) -> tuple[str, str]:
        """Save train/eval splits. Returns (train_path, eval_path)."""
        raise NotImplementedError
