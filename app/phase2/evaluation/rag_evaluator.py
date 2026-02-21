"""STUB: RAG evaluation framework (Phase 2).

Evaluates retrieval and generation quality using standard RAG metrics:
- Retrieval: Precision@K, Recall@K, NDCG, MRR
- Generation: faithfulness, answer relevance, context precision/recall
- End-to-end: RAGAS framework metrics

Phase 2 implementation:
- Use RAGAS library for automated RAG evaluation
- Build ground-truth QA dataset from expert-annotated finance QAs
- Run nightly evaluation pipeline against production index
- Track metrics in Prometheus/Grafana dashboard
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvalSample:
    """A single evaluation sample with question, ground truth, and system output."""
    question: str
    ground_truth_answer: str
    ground_truth_contexts: list[str]
    retrieved_contexts: list[str] = field(default_factory=list)
    generated_answer: str = ""


@dataclass
class EvalMetrics:
    """Aggregated evaluation metrics across a test set."""
    faithfulness: float = 0.0          # Are answers grounded in retrieved context?
    answer_relevance: float = 0.0      # Is the answer relevant to the question?
    context_precision: float = 0.0     # Are retrieved chunks relevant?
    context_recall: float = 0.0        # Are relevant chunks retrieved?
    ndcg_at_k: float = 0.0            # Normalized Discounted Cumulative Gain
    mrr: float = 0.0                   # Mean Reciprocal Rank
    sample_count: int = 0


class RAGEvaluator:
    """STUB: Comprehensive RAG pipeline evaluator.

    Phase 2 implementation:
    - pip install ragas datasets
    - Build eval dataset from expert-curated finance QAs
    - Run automated evaluation with LLM-as-judge (Claude)
    - Export metrics to Prometheus for Grafana dashboards
    """

    def __init__(
        self,
        eval_dataset_path: str = "./data/eval_dataset.json",
        judge_model: str = "claude-sonnet-4-6",
    ) -> None:
        self.eval_dataset_path = eval_dataset_path
        self.judge_model = judge_model
        raise NotImplementedError("RAGEvaluator is a Phase 2 stub.")

    def load_eval_dataset(self) -> list[EvalSample]:
        """Load ground-truth QA evaluation samples."""
        raise NotImplementedError

    async def evaluate_retrieval(self, samples: list[EvalSample]) -> EvalMetrics:
        """Compute retrieval metrics (precision, recall, NDCG, MRR)."""
        raise NotImplementedError

    async def evaluate_generation(self, samples: list[EvalSample]) -> EvalMetrics:
        """Compute generation metrics (faithfulness, relevance) using LLM-as-judge."""
        raise NotImplementedError

    async def run_full_evaluation(self) -> EvalMetrics:
        """Run complete end-to-end evaluation pipeline."""
        raise NotImplementedError

    def export_metrics(self, metrics: EvalMetrics, output_path: str) -> None:
        """Export evaluation results to JSON."""
        raise NotImplementedError
