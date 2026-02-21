"""STUB: LoRA fine-tuning trainer for finance domain adaptation (Phase 2).

This module is a design hook only. The interface is defined here so that
Phase 2 implementation can slot in without modifying call sites.

Phase 2 implementation plan:
- Use HuggingFace PEFT library for LoRA adapters
- Base model: a financial-domain LLM (e.g. FinGPT, Llama-3 with finance instruct)
- Training data: collected via COLLECT_TRAINING_DATA=true env var in GenerationService
- Dataset format: {"question": str, "context": str, "answer": str} JSONL
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LoRAConfig:
    """Configuration for LoRA fine-tuning."""
    base_model: str = "meta-llama/Llama-3-8b-instruct"
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: list[str] = None  # e.g. ["q_proj", "v_proj"]
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    output_dir: str = "./models/lora-finance"

    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


class LoRATrainer:
    """STUB: Fine-tune a base LLM with LoRA adapters on finance QA data.

    Phase 2 implementation requires:
    - pip install peft bitsandbytes accelerate trl
    - GPU with ≥24GB VRAM (or multi-GPU with DeepSpeed)
    """

    def __init__(self, config: LoRAConfig) -> None:
        self.config = config
        raise NotImplementedError(
            "LoRATrainer is a Phase 2 stub. "
            "Implement with HuggingFace PEFT + TRL SFTTrainer."
        )

    def prepare_model(self) -> None:
        """Load base model in 4-bit quantization and attach LoRA adapters."""
        raise NotImplementedError

    def train(self, train_dataset_path: str, eval_dataset_path: Optional[str] = None) -> str:
        """Run fine-tuning and return path to saved adapter weights."""
        raise NotImplementedError

    def push_to_registry(self, adapter_path: str, version: str) -> None:
        """Register the adapter in the model registry."""
        raise NotImplementedError
