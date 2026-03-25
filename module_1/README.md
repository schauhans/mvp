# Module 1 — XHS Trend Object Builder

This module has two components:

1. **`xhs_scraper_live.py`** — Scrapes live posts from Xiaohongshu, preserves all raw data, anonymizes creators, and AI-captions images.
2. **`xhs_trend_builder.py`** — Takes the scraped posts and clusters them into structured Trend Objects.

Run them in order:

```bash
# Step 1: Scrape live XHS data  (use .venv/bin/python3 on Mac)
.venv/bin/python3 xhs_scraper_live.py --keywords "美白" "防晒" --times 3 --category beauty

# Step 2: Build trend objects from the scraped data
.venv/bin/python3 xhs_trend_builder.py
```

---

## Setup

### 1. Create a virtual environment and install dependencies

> **Mac note:** Use `python3` and `pip3` — `python`/`pip` without the `3` do not exist by default on macOS.

```bash
# From inside the module_1 folder:
python3 -m venv .venv
.venv/bin/pip install DrissionPage pandas tqdm openpyxl
```

### 2. Configure API key

Set your OpenRouter key in the root `.env` file (one directory up, already created):

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_MODEL=openai/gpt-4o-mini
```

### 3. Chrome + XHS login (first run only)

- Chrome browser must be installed.
- On the **first run**, a Chrome window will open showing XHS.
- Log in with your XHS credentials or scan the QR code with your phone app.
- After that, Chrome remembers the session — no re-login needed.

---

## xhs_scraper_live.py — full reference

```
usage: xhs_scraper_live.py [-h] --keywords KEYWORD [KEYWORD ...]
                            [--times N] [--category CATEGORY]
                            [--extra-info] [--no-caption]

Options:
  --keywords / -k   One or more XHS search keywords (required)
                    e.g. --keywords "美白" "Dior" "防晒霜"
  --times / -t      Scroll pages per keyword (default: 3, more = more posts)
  --category / -c   Category label for the posts (default: beauty)
  --extra-info      Fetch full detail per post: date, saves, comment count,
                    description, hashtags. Slower but richer.
  --no-caption      Skip AI image captioning (no API calls for images)
```

### Examples

```bash
# Fast run — no detail page visits, no image AI
.venv/bin/python3 xhs_scraper_live.py --keywords "Dior" --times 2 --no-detail --no-caption

# Full run — visits each post for images, captions, hashtags, date
.venv/bin/python3 xhs_scraper_live.py --keywords "美白" "防晒" --times 5 --category beauty

# Multiple brands, skip AI captions (faster)
.venv/bin/python3 xhs_scraper_live.py --keywords "Dior" "Chanel" "YSL" --times 3 --no-caption
```

---

## What gets saved

| File | Contents |
|------|----------|
| `data/xhs_raw_posts.json` | **Completely raw scraped data — nothing changed.** Creator names, titles, captions, hashtags exactly as on XHS. |
| `data/xhs_posts.json` | Same content, but creator usernames replaced with anonymous IDs (e.g. `user_a3f9b12c`). AI image captions added per post. This file feeds the trend builder. |

### Anonymization

- Creator usernames are replaced using a **one-way SHA-256 hash**.
- The same creator will always get the same anonymous ID across runs.
- The original name is **never stored** in `xhs_posts.json`.
- The original name **is** stored in `xhs_raw_posts.json` under `raw_creator`.

### Image captions

- For each post that has an image URL, the AI is asked to describe:
  - What products are shown
  - The visual aesthetic, colors, styling
  - Any visible text or branding
- Caption is stored as `image_caption` in `xhs_posts.json`.

---

## Data schema

### `xhs_raw_posts.json` (per record)

```json
{
  "post_id": "live_0001",
  "scraped_at": "2026-03-25T10:00:00Z",
  "keyword": "美白",
  "post_link": "https://www.xiaohongshu.com/...",
  "title": "原始标题",
  "raw_creator": "原始用户名",
  "likes": 8542,
  "date": "2026-02-15",
  "saves": 1200,
  "comments": 423,
  "caption": "原始正文",
  "hashtags": ["#美白", "#护肤"],
  "image_url": "https://..."
}
```

### `xhs_posts.json` (per record, feeds trend builder)

```json
{
  "post_id": "live_0001",
  "keyword": "美白",
  "category": "beauty",
  "date": "2026-02-15",
  "title": "原始标题",
  "caption": "原始正文",
  "hashtags": ["#美白", "#护肤"],
  "likes": 8542,
  "comments": 423,
  "saves": 1200,
  "creator": "user_a3f9b12c",
  "post_link": "https://...",
  "cover_url": "https://...thumbnail...",
  "all_image_urls": ["https://...img1...", "https://...img2..."],
  "is_video": false,
  "video_url": "",
  "image_caption": "The image shows a white serum bottle on a marble surface..."
}
```

`all_image_urls` contains every image from the post gallery. `cover_url` is the card thumbnail. For video posts, `is_video` is `true` and `video_url` has the stream URL.

---

## xhs_trend_builder.py

Reads `data/xhs_posts.json` and clusters posts into Trend Objects.

```bash
python xhs_trend_builder.py
```

For LLM-assisted labeling, enable it in `data/run_config.json`:

```json
{
  "llm": {
    "enabled": true,
    "model": "openai/gpt-4o-mini"
  }
}
```

Output is saved to `outputs/runs/`.
