#!/usr/bin/env python3
"""Seed the vector store with sample financial documents.

Usage:
    python scripts/seed_documents.py --dir ./data/sample_docs --url http://localhost:8000
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx


async def upload_pdf(client: httpx.AsyncClient, filepath: Path, base_url: str) -> dict:
    """Upload a single PDF to the ingestion endpoint."""
    filename = filepath.name
    print(f"  Uploading: {filename} ({filepath.stat().st_size / 1024:.1f} KB)")

    with open(filepath, "rb") as f:
        content = f.read()

    # Try to infer metadata from filename
    # Expected pattern: TICKER_REPORTTYPE_YEAR.pdf (e.g., AAPL_10-K_2023.pdf)
    parts = filename.replace(".pdf", "").split("_")
    form_data: dict = {}
    if len(parts) >= 1:
        form_data["ticker"] = parts[0].upper()
    if len(parts) >= 2:
        form_data["report_type"] = parts[1]
    if len(parts) >= 3:
        try:
            form_data["year"] = int(parts[2])
        except ValueError:
            pass

    response = await client.post(
        f"{base_url}/documents/upload",
        files={"file": (filename, content, "application/pdf")},
        data=form_data,
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()


async def main():
    parser = argparse.ArgumentParser(description="Seed Finance RAG with sample documents")
    parser.add_argument("--dir", default="./data/sample_docs", help="Directory of PDF files")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--pattern", default="*.pdf", help="File glob pattern")
    args = parser.parse_args()

    doc_dir = Path(args.dir)
    if not doc_dir.exists():
        print(f"ERROR: Directory not found: {doc_dir}")
        sys.exit(1)

    pdf_files = list(doc_dir.glob(args.pattern))
    if not pdf_files:
        print(f"No PDF files found in {doc_dir}")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF file(s) in {doc_dir}")
    print(f"Target API: {args.url}\n")

    async with httpx.AsyncClient() as client:
        # Health check
        try:
            health = await client.get(f"{args.url}/health", timeout=10.0)
            health_data = health.json()
            print(f"API Health: {health_data.get('status', 'unknown')}")
            if health_data.get("status") != "ok":
                print(f"  Services: {health_data.get('services', {})}")
        except Exception as e:
            print(f"WARNING: Could not reach API at {args.url}: {e}")

        total_chunks = 0
        success_count = 0

        for pdf_path in sorted(pdf_files):
            try:
                result = await upload_pdf(client, pdf_path, args.url)
                chunks = result.get("chunk_count", 0)
                total_chunks += chunks
                success_count += 1
                print(f"    ✓ {result.get('document_id', '?')} — {chunks} chunks "
                      f"[{result.get('company', '?')} {result.get('year', '?')}]")
            except httpx.HTTPStatusError as e:
                print(f"    ✗ FAILED: {pdf_path.name} — HTTP {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                print(f"    ✗ ERROR: {pdf_path.name} — {e}")

    print(f"\nDone: {success_count}/{len(pdf_files)} documents ingested, {total_chunks} total chunks")


if __name__ == "__main__":
    asyncio.run(main())
