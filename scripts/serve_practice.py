#!/usr/bin/env python3
"""Serve the GRE practice UI and ratings API."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
QUESTIONS_FILE = ROOT / "data" / "questions.jsonl"
RATINGS_FILE = ROOT / "data" / "ratings.json"
TIMES_FILE = ROOT / "data" / "times.json"
COMMENTS_FILE = ROOT / "data" / "comments.json"
WORDS_FILE = ROOT / "data" / "words.jsonl"
WORD_RATINGS_FILE = ROOT / "data" / "word_ratings.json"
WORD_TIMES_FILE = ROOT / "data" / "word_times.json"
WORD_COMMENTS_FILE = ROOT / "data" / "word_comments.json"
HOST = "127.0.0.1"
PORT = 8765
DATA_DIR = ROOT / "data"


def load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def load_questions() -> list[dict]:
    return load_jsonl(QUESTIONS_FILE)


def load_words() -> list[dict]:
    return load_jsonl(WORDS_FILE)


def load_ratings() -> dict[str, int]:
    if not RATINGS_FILE.exists():
        return {}
    return {k: int(v) for k, v in json.loads(RATINGS_FILE.read_text(encoding="utf-8")).items()}


def save_ratings(ratings: dict[str, int]) -> None:
    RATINGS_FILE.write_text(json.dumps(ratings, indent=2) + "\n", encoding="utf-8")


def load_times() -> dict[str, int]:
    if not TIMES_FILE.exists():
        return {}
    return {k: int(v) for k, v in json.loads(TIMES_FILE.read_text(encoding="utf-8")).items()}


def save_times(times: dict[str, int]) -> None:
    TIMES_FILE.write_text(json.dumps(times, indent=2) + "\n", encoding="utf-8")


def load_comments() -> dict[str, str]:
    if not COMMENTS_FILE.exists():
        return {}
    return {k: str(v) for k, v in json.loads(COMMENTS_FILE.read_text(encoding="utf-8")).items()}


def save_comments(comments: dict[str, str]) -> None:
    COMMENTS_FILE.write_text(json.dumps(comments, indent=2) + "\n", encoding="utf-8")


def load_word_ratings() -> dict[str, int]:
    if not WORD_RATINGS_FILE.exists():
        return {}
    return {k: int(v) for k, v in json.loads(WORD_RATINGS_FILE.read_text(encoding="utf-8")).items()}


def save_word_ratings(ratings: dict[str, int]) -> None:
    WORD_RATINGS_FILE.write_text(json.dumps(ratings, indent=2) + "\n", encoding="utf-8")


def ensure_data_files() -> None:
    """Create data/ and seed ratings files from jsonl sources when missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not RATINGS_FILE.exists():
        ratings: dict[str, int] = {}
        for question in load_jsonl(QUESTIONS_FILE):
            ratings[str(question["post_id"])] = 0
        save_ratings(ratings)
        print(f"created {RATINGS_FILE.relative_to(ROOT)} ({len(ratings)} questions)")

    if not WORD_RATINGS_FILE.exists():
        word_ratings: dict[str, int] = {}
        for entry in load_jsonl(WORDS_FILE):
            word_ratings[str(entry["word"])] = 0
        save_word_ratings(word_ratings)
        print(f"created {WORD_RATINGS_FILE.relative_to(ROOT)} ({len(word_ratings)} words)")


def load_word_times() -> dict[str, int]:
    if not WORD_TIMES_FILE.exists():
        return {}
    return {k: int(v) for k, v in json.loads(WORD_TIMES_FILE.read_text(encoding="utf-8")).items()}


def save_word_times(times: dict[str, int]) -> None:
    WORD_TIMES_FILE.write_text(json.dumps(times, indent=2) + "\n", encoding="utf-8")


def load_word_comments() -> dict[str, str]:
    if not WORD_COMMENTS_FILE.exists():
        return {}
    return {k: str(v) for k, v in json.loads(WORD_COMMENTS_FILE.read_text(encoding="utf-8")).items()}


def save_word_comments(comments: dict[str, str]) -> None:
    WORD_COMMENTS_FILE.write_text(json.dumps(comments, indent=2) + "\n", encoding="utf-8")


def compute_stats(
    ratings: dict[str, int],
    times: dict[str, int] | None = None,
    comments: dict[str, str] | None = None,
) -> dict:
    counts = {str(i): 0 for i in range(6)}
    rated: list[int] = []
    for value in ratings.values():
        rating = max(0, min(5, int(value)))
        counts[str(rating)] += 1
        if rating > 0:
            rated.append(rating)
    average = sum(rated) / len(rated) if rated else 0.0
    if times is not None:
        nonzero_times = [t for post_id in ratings if (t := times.get(post_id, 0)) > 0]
        average_time = sum(nonzero_times) / len(nonzero_times) if nonzero_times else 0.0
    else:
        average_time = 0.0
    payload = {"counts": counts, "average": average, "average_time": average_time, "ratings": ratings}
    if times is not None:
        payload["times"] = times
    if comments is not None:
        payload["comments"] = comments
    return payload


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/questions":
            self._send_json(200, {"questions": load_questions()})
            return

        if path == "/api/ratings":
            self._send_json(200, compute_stats(load_ratings(), load_times(), load_comments()))
            return

        if path == "/api/words":
            self._send_json(200, {"words": load_words()})
            return

        if path == "/api/word-ratings":
            self._send_json(200, compute_stats(load_word_ratings(), load_word_times(), load_word_comments()))
            return

        if path in ("/", "/index.html"):
            self._serve_file(UI_DIR / "index.html")
            return

        if path.startswith("/"):
            candidate = UI_DIR / path.lstrip("/")
            if candidate.is_file():
                self._serve_file(candidate)
                return

        self._send_error_json(404, "not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/ratings":
            self._save_rating(
                id_key="post_id",
                load_ratings=load_ratings,
                save_ratings=save_ratings,
                load_times=load_times,
                save_times=save_times,
                load_comments=load_comments,
                unknown_label="post_id",
            )
            return

        if path == "/api/word-ratings":
            self._save_rating(
                id_key="word",
                load_ratings=load_word_ratings,
                save_ratings=save_word_ratings,
                load_times=load_word_times,
                save_times=save_word_times,
                load_comments=load_word_comments,
                unknown_label="word",
            )
            return

        if path == "/api/comments":
            self._save_comment(
                id_key="post_id",
                load_ratings=load_ratings,
                load_times=load_times,
                load_comments=load_comments,
                save_comments=save_comments,
                unknown_label="post_id",
            )
            return

        if path == "/api/word-comments":
            self._save_comment(
                id_key="word",
                load_ratings=load_word_ratings,
                load_times=load_word_times,
                load_comments=load_word_comments,
                save_comments=save_word_comments,
                unknown_label="word",
            )
            return

        self._send_error_json(404, "not found")

    def _save_rating(
        self,
        *,
        id_key: str,
        load_ratings,
        save_ratings,
        load_times,
        save_times,
        load_comments,
        unknown_label: str,
    ) -> None:
        try:
            body = self._read_json_body() or {}
            item_id = str(body.get(id_key, ""))
            rating = int(body["rating"])
            seconds = int(body["seconds"])
        except (KeyError, TypeError, ValueError):
            self._send_error_json(400, f"expected {{ {id_key}, rating, seconds }}")
            return

        if rating < 1 or rating > 5:
            self._send_error_json(400, "rating must be 1–5")
            return

        if seconds < 0:
            self._send_error_json(400, "seconds must be >= 0")
            return

        ratings = load_ratings()
        if item_id not in ratings:
            self._send_error_json(400, f"unknown {unknown_label}: {item_id}")
            return

        ratings[item_id] = rating
        save_ratings(ratings)

        times = load_times()
        times[item_id] = seconds
        save_times(times)

        self._send_json(200, compute_stats(ratings, times, load_comments()))

    def _save_comment(
        self,
        *,
        id_key: str,
        load_ratings,
        load_times,
        load_comments,
        save_comments,
        unknown_label: str,
    ) -> None:
        try:
            body = self._read_json_body() or {}
            item_id = str(body.get(id_key, ""))
            comment = str(body.get("comment", ""))
        except (TypeError, ValueError):
            self._send_error_json(400, f"expected {{ {id_key}, comment }}")
            return

        ratings = load_ratings()
        if item_id not in ratings:
            self._send_error_json(400, f"unknown {unknown_label}: {item_id}")
            return

        comments = load_comments()
        if comment.strip():
            comments[item_id] = comment
        else:
            comments.pop(item_id, None)
        save_comments(comments)

        self._send_json(200, compute_stats(ratings, load_times(), comments))

    def _serve_file(self, path: Path) -> None:
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    ensure_data_files()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"serving at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
