# Agent notes

## Goal
Pipeline: scrape → store in-repo → display. Do not invent questions.

## Data
- `data/post_links.json` — 2561 URLs in `all_links`. Format: `https://gre.myprepclub.com/forum/{slug}-{topic_id}.html#p{post_id}`. Some entries lack `#p{post_id}`; skip those.
- `data/questions.jsonl` — scraped questions, one JSON object per line. Fields: `source_url`, `post_id`, `body_html`, `body_text`, `official_answer`. Re-scraping a `post_id` replaces its line.
- `data/ratings.json` — self-ratings by `post_id` (`0` unrated, `1–5` ability). Gitignored; seed via `scripts/seed_ratings.py`.
- `data/times.json` — seconds per question, saved on rate. Gitignored.

## Scraping (done)
- `scripts/scrape_one.py [url]` — scrape one URL (defaults to first in `all_links`).
- `scripts/scrape_batch.py [n]` — scrape next `n` unscraped URLs; 10s delay between fetches.
- Stdlib only. User-Agent: `gre-practice-bank-scraper/0.1`.
- Auth: credentials in `.env` (`GRE_PREPCLUB_USERNAME`, `GRE_PREPCLUB_PASSWORD`). Login POST to `/forum/ucp.php?mode=login`. Verify via `ucp.php?mode=logout` in response HTML.
- HTML: post wrapper `id="p_{post_id}"` (underscore); URL fragment `#p{post_id}`. Question in `div.item.text`; official answer in `div#spoiler_{post_id}.downRow`. Exclude `twoRowsBlock` and `post_signature` from question body. Gated answer text means login failed.

## Practice UI (done)
Workflow: scrape all → `python scripts/seed_ratings.py` → `python scripts/serve_practice.py` → `http://127.0.0.1:8765`.

- `ui/` — static HTML/CSS/JS + MathJax CDN. Dark theme.
- `scripts/serve_practice.py` — serves UI; `GET /api/questions`, `GET /api/ratings`, `POST /api/ratings` (`{post_id, rating, seconds}`).
- Reveal answer → rate 1–5 (saves rating + time, auto-advances). Timer auto-starts per question, pause/play icons, stops on reveal.
- Next: weighted by rating tier (80/10/5/3/1/1 for 0–5). Previous: session history.
- Header: rating distribution bar, avg rating (★), avg time (clock; includes unrated as 0s). Revisited questions show last rating + time.
- Preserve `source_url` attribution.

## Rules
- Rate-limit scrapes. Prefer local data over re-fetching.
- Preserve attribution (`source_url` per question).
