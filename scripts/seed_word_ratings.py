#!/usr/bin/env python3
"""Seed data/word_ratings.json with 0 for every word in words.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS_FILE = ROOT / "data" / "words.jsonl"
WORD_RATINGS_FILE = ROOT / "data" / "word_ratings.json"


def main() -> int:
    if not WORDS_FILE.exists():
        print(f"words file not found: {WORDS_FILE}", file=sys.stderr)
        return 1

    ratings: dict[str, int] = {}
    for line in WORDS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        word = json.loads(line)["word"]
        ratings[word] = 0

    if not ratings:
        print("no words found in words.jsonl", file=sys.stderr)
        return 1

    WORD_RATINGS_FILE.write_text(json.dumps(ratings, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(ratings)} word ratings to {WORD_RATINGS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
