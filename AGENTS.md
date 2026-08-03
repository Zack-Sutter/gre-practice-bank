# Agent notes

## Goal
Pipeline: scrape → store in-repo → display. Do not invent questions.

## Data
- `data/post_links.json` — 2561 URLs in `all_links`. Format: `https://gre.myprepclub.com/forum/{slug}-{topic_id}.html#p{post_id}`. Some entries lack `#p{post_id}`; skip those.
- `data/questions.jsonl` — scraped questions, one JSON object per line. Fields: `source_url`, `post_id`, `body_html`, `body_text`, `official_answer`. Re-scraping a `post_id` replaces its line. (6 scraped so far.)

## Scraping (done)
- `scripts/scrape_one.py [url]` — scrape one URL (defaults to first in `all_links`).
- `scripts/scrape_batch.py [n]` — scrape next `n` unscraped URLs; 10s delay between fetches.
- Stdlib only. User-Agent: `gre-practice-bank-scraper/0.1`.
- Auth: credentials in `.env` (`GRE_PREPCLUB_USERNAME`, `GRE_PREPCLUB_PASSWORD`). Login POST to `/forum/ucp.php?mode=login`. Verify via `ucp.php?mode=logout` in response HTML.
- HTML: post wrapper `id="p_{post_id}"` (underscore); URL fragment `#p{post_id}`. Question in `div.item.text`; official answer in `div#spoiler_{post_id}.downRow`. Exclude `twoRowsBlock` and `post_signature` from question body. Gated answer text means login failed.

## Next: practice display
Build a UI to work through questions with answers hidden (reveal on demand). Read from `data/questions.jsonl`. Preserve `source_url` attribution.

## Rules
- Rate-limit scrapes. Prefer local data over re-fetching.
- Preserve attribution (`source_url` per question).
