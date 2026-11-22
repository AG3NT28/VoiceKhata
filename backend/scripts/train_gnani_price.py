#!/usr/bin/env python3
"""Train Gnani bias + NLU few-shots from the multilingual price-comparison JSONL.

Gnani Prisma has no offline fine-tune API. This script:
  1. Copies / refreshes backend/data/voicekhata_price_comparison_multilingual.jsonl
  2. Builds keyterms + topic for STT
  3. Loads few-shots for FIND_WHOLESALE into the NLU prompt path
  4. Prints a training summary (counts, languages, sample keyterms)

Usage:
  python scripts/train_gnani_price.py
  python scripts/train_gnani_price.py --source "C:/Users/saisu/Desktop/voicekhata_price_comparison_multilingual.jsonl"
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_SOURCE = Path.home() / "Desktop" / "voicekhata_price_comparison_multilingual.jsonl"
TARGET = ROOT / "data" / "voicekhata_price_comparison_multilingual.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Gnani from price-comparison JSONL")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to multilingual price-comparison JSONL",
    )
    args = parser.parse_args()
    source: Path = args.source

    if not source.exists():
        print(f"ERROR: source JSONL not found: {source}")
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, TARGET)
    print(f"Copied {source} -> {TARGET} ({TARGET.stat().st_size} bytes)")

    # Clear lru caches so fresh data is loaded
    from app.ai import price_dataset as pd

    pd.load_price_examples.cache_clear()
    pd.gnani_keyterms.cache_clear()

    summary = pd.training_summary()
    keyterms = pd.gnani_keyterms(30)
    shots = pd.few_shot_from_price_dataset(5)

    print("\n=== Gnani price training summary ===")
    print(f"examples       : {summary['examples']}")
    print(f"languages      : {summary['languages']}")
    print(f"runtime intents: {summary['runtime_intents']}")
    print(f"keyterms       : {summary['keyterms']}")
    print(f"mode           : {summary['gnani_mode']}")
    print(f"topic          : {pd.gnani_topic()[:120]}...")
    print(f"sample keyterms: {keyterms}")
    print("\nSample few-shots:")
    for spoken, payload in shots:
        print(f"  [{payload['intent']}] {spoken[:80]}")
        print(f"      query={payload['entities'].get('query')!r}")

    # Warm prompt merge path
    from app.ai.prompts import FEW_SHOT_EXAMPLES

    price_shots = sum(1 for _, p in FEW_SHOT_EXAMPLES if p.get("intent") == "FIND_WHOLESALE")
    print(f"\nPrompt few-shots total={len(FEW_SHOT_EXAMPLES)} FIND_WHOLESALE={price_shots}")
    print("Training complete. STT will use keyterms+topic on next request.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
