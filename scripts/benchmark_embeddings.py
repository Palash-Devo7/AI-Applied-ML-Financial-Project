#!/usr/bin/env python3
"""Benchmark FinBERT embedding throughput and latency.

Usage:
    python scripts/benchmark_embeddings.py --batch-sizes 1 4 8 16 --samples 100
"""
import argparse
import asyncio
import statistics
import sys
import time


async def benchmark_embedding(
    model_name: str,
    strategy: str,
    batch_size: int,
    texts: list[str],
) -> dict:
    """Benchmark a single batch size configuration."""
    from app.services.embedding_service import EmbeddingService

    service = EmbeddingService(
        model_name=model_name,
        strategy=strategy,
        device="cpu",
        batch_size=batch_size,
    )

    # Warm-up run
    await service.embed_texts(texts[:batch_size])

    # Timed runs
    latencies: list[float] = []
    n_runs = max(3, 100 // max(len(texts), 1))

    for _ in range(n_runs):
        t0 = time.perf_counter()
        await service.embed_texts(texts)
        latencies.append((time.perf_counter() - t0) * 1000)

    throughput = len(texts) * 1000 / statistics.mean(latencies)

    return {
        "batch_size": batch_size,
        "n_texts": len(texts),
        "n_runs": n_runs,
        "mean_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 2) if len(latencies) > 1 else latencies[0],
        "throughput_per_sec": round(throughput, 2),
    }


def generate_sample_texts(n: int, length: int = 200) -> list[str]:
    """Generate synthetic financial text samples."""
    templates = [
        "The company reported net revenues of ${amount} billion for fiscal year {year}, representing an increase of {pct}% year-over-year.",
        "Risk factors include significant competition in the {sector} sector, regulatory changes, and supply chain disruptions.",
        "Total operating expenses were ${amount} million, including research and development costs of ${rd} million.",
        "The board of directors declared a quarterly dividend of ${div} per share, payable on {date}.",
        "Earnings per diluted share were ${eps} compared to ${eps_prior} in the prior year period.",
    ]
    texts = []
    for i in range(n):
        template = templates[i % len(templates)]
        texts.append(template.format(
            amount=round(10 + i * 0.5, 1),
            year=2020 + (i % 4),
            pct=round(5 + i * 0.3, 1),
            sector=["technology", "healthcare", "financial"][i % 3],
            rd=round(1 + i * 0.1, 1),
            div=round(0.1 + i * 0.01, 2),
            date="March 15, 2024",
            eps=round(1.5 + i * 0.1, 2),
            eps_prior=round(1.3 + i * 0.1, 2),
        ))
    return texts


async def main():
    parser = argparse.ArgumentParser(description="Benchmark FinBERT embeddings")
    parser.add_argument("--model", default="ProsusAI/finbert")
    parser.add_argument("--strategy", choices=["cls", "mean"], default="cls")
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=[1, 4, 8, 16])
    parser.add_argument("--samples", type=int, default=32, help="Number of sample texts")
    args = parser.parse_args()

    print(f"FinBERT Embedding Benchmark")
    print(f"  Model: {args.model}")
    print(f"  Strategy: {args.strategy}")
    print(f"  Samples: {args.samples}")
    print(f"  Batch sizes: {args.batch_sizes}")
    print()

    texts = generate_sample_texts(args.samples)

    print(f"{'Batch':>6}  {'Mean ms':>10}  {'p50 ms':>8}  {'p95 ms':>8}  {'texts/sec':>10}")
    print("-" * 50)

    for batch_size in args.batch_sizes:
        result = await benchmark_embedding(args.model, args.strategy, batch_size, texts)
        print(
            f"{result['batch_size']:>6}  "
            f"{result['mean_ms']:>10.1f}  "
            f"{result['p50_ms']:>8.1f}  "
            f"{result['p95_ms']:>8.1f}  "
            f"{result['throughput_per_sec']:>10.1f}"
        )

    print()
    print("Benchmark complete.")


if __name__ == "__main__":
    # Add project root to path
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
