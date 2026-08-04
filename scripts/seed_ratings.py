#!/usr/bin/env python3
"""Seed data/ratings.json with 0 for every post_id in questions.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "data" / "questions.jsonl"
RATINGS_FILE = ROOT / "data" / "ratings.json"


def main() -> int:
    if not QUESTIONS_FILE.exists():
        print(f"questions file not found: {QUESTIONS_FILE}", file=sys.stderr)
        return 1

    ratings: dict[str, int] = {}
    for line in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        post_id = json.loads(line)["post_id"]
        ratings[post_id] = 0

    if not ratings:
        print("no questions found in questions.jsonl", file=sys.stderr)
        return 1

    RATINGS_FILE.write_text(json.dumps(ratings, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(ratings)} ratings to {RATINGS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
