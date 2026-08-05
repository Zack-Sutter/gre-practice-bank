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
HOST = "127.0.0.1"
PORT = 8765


def load_questions() -> list[dict]:
    questions: list[dict] = []
    if not QUESTIONS_FILE.exists():
        return questions
    for line in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            questions.append(json.loads(line))
    return questions


def load_ratings() -> dict[str, int]:
    if not RATINGS_FILE.exists():
        raise FileNotFoundError("ratings.json not found; run scripts/seed_ratings.py first")
    return {k: int(v) for k, v in json.loads(RATINGS_FILE.read_text(encoding="utf-8")).items()}


def save_ratings(ratings: dict[str, int]) -> None:
    RATINGS_FILE.write_text(json.dumps(ratings, indent=2) + "\n", encoding="utf-8")


def load_times() -> dict[str, int]:
    if not TIMES_FILE.exists():
        return {}
    return {k: int(v) for k, v in json.loads(TIMES_FILE.read_text(encoding="utf-8")).items()}


def save_times(times: dict[str, int]) -> None:
    TIMES_FILE.write_text(json.dumps(times, indent=2) + "\n", encoding="utf-8")


def compute_stats(ratings: dict[str, int], times: dict[str, int] | None = None) -> dict:
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
            try:
                ratings = load_ratings()
            except FileNotFoundError as exc:
                self._send_error_json(500, str(exc))
                return
            self._send_json(200, compute_stats(ratings, load_times()))
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
        if path != "/api/ratings":
            self._send_error_json(404, "not found")
            return

        try:
            body = self._read_json_body() or {}
            post_id = str(body.get("post_id", ""))
            rating = int(body["rating"])
            seconds = int(body["seconds"])
        except (KeyError, TypeError, ValueError):
            self._send_error_json(400, "expected { post_id, rating, seconds }")
            return

        if rating < 1 or rating > 5:
            self._send_error_json(400, "rating must be 1–5")
            return

        if seconds < 0:
            self._send_error_json(400, "seconds must be >= 0")
            return

        try:
            ratings = load_ratings()
        except FileNotFoundError as exc:
            self._send_error_json(500, str(exc))
            return

        if post_id not in ratings:
            self._send_error_json(400, f"unknown post_id: {post_id}")
            return

        ratings[post_id] = rating
        save_ratings(ratings)

        times = load_times()
        times[post_id] = seconds
        save_times(times)

        self._send_json(200, compute_stats(ratings, times))

    def _serve_file(self, path: Path) -> None:
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"serving at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
