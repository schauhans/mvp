# Module 3 — I/O Contract

**Audience:** Developer connecting Module 2 output or Module 3 output to another system.
**Version:** 2026-03-29

---

## Inputs

### Source Priority

Module 3 reads trend data from two sources in priority order:

1. **`module_2/outputs/output_shortlist.json`** — used when Module 2 has been run for the same brand. Module 3 checks the `brand` field before loading; if the cached output is for a different brand it is skipped to prevent stale data bleeding across runs.
2. **`module_3/trend_brief_agent/trend_shortlist.json`** — fallback for standalone testing. Used when Module 2 output is absent or brand-mismatched.

### From `module_2/outputs/output_shortlist.json` → `shortlist[]`

These are the fields Module 3 reads via `normalise_from_module2()`. Fields not listed are ignored.

| Field | Type | Required | Maps To / Used For |
|---|---|---|---|
| `trend_id` | string | Required | Card identifier, section heading (`## t01: ...`), run log |
| `label` | string | Required | `trend_label` — card title and LLM prompt |
| `category` | string | Optional | Card header; may be empty string if Module 1 ran without a category filter |
| `confidence` | string | Optional | Used as `brand_relevance` proxy (high/medium/low) for trend selection |
| `why_selected` | string | Required | Maps to `cluster_summary` — used in Trend Overview LLM prompt |
| `evidence_references` | string[] | Optional | `[0]` → `top_post_example`; `[1:]` → `trending_hashtags` |
| `metric_signal.post_count` | int | Required | `assess_confidence()` threshold check; DATA SIGNAL display |
| `metric_signal.avg_engagement` | float | Required | Converted to `engagement_rate` via `min(avg_engagement / 10000, 1.0)` |
| `brand` | string | Required | Brand check — if this doesn't match the current run's brand, the cache is skipped |
| `city_distribution` | dict | Optional | e.g. `{"上海": 4, "广东": 3}` — used for city relevance ranking and card display |

**Fields NOT passed from Module 2:**
- `city` — Module 2 does not attach a city. Module 3 stamps the user-selected city onto all trends at runtime via `select_trends()`. City relevance is surfaced instead via `city_distribution`.
- `week_on_week_growth` — Module 1 computes this from post date buckets and stores it as `momentum_signal`. Module 2 passes it through as `week_on_week_growth`. Falls back to `"+15%"` only when absent. The fallback path in `normalise_from_fallback` hardcodes `"+20%"` for standalone testing.

### From `module_3/trend_brief_agent/personas/{brand}_personas.json` → `personas[]`

| Field | Type | Required | Used For |
|---|---|---|---|
| `id` | string | Required | Match lookup key after LLM persona selection |
| `name` | string | Required | Displayed in CLIENT MATCH section |
| `summary` | string | Required | "Who they are" in card |
| `trend_receptivity` | string | Required | Passed to persona match LLM prompt to guide selection |
| `avoid` | string | Required | "This trend is NOT for" line in card |

### CLI Arguments (when called from `main.py`)

| Argument | Required | Description |
|---|---|---|
| `--brand` | Required | Brand name; used for brand cache check and persona file selection |
| `--city` | Required | Store city; stamped onto all trends and controls city tone guideline |

---

## Pre-Card Decision Logic

Before generating cards, Module 3 applies three named failure checks to each trend. Any failure skips the card and logs the reason.

| Failure Type | Trigger | Consequence |
|---|---|---|
| `MISSING_EVIDENCE` | Fewer than 3 of: `post_count`, `engagement_rate`, `week_on_week_growth`, `cluster_summary` are present | Card skipped — cannot make evidence-anchored claims |
| `MISSING_CONTEXT` | `city` field absent | Card skipped — city-specific tone cannot be applied |
| `WEAK_SIGNAL` | `week_on_week_growth < +10%` AND `engagement_rate < 0.08` | Card skipped — insufficient momentum to recommend this week |

If fewer than 3 trends pass all checks, the agent lowers the `brand_relevance` threshold to include `medium` relevance trends and warns in the card header.

### City Relevance Ranking

`compute_composite_score()` accepts the selected city and applies a bonus of up to +5 points based on `city_distribution`. A trend where 100% of geolocated posts are from the selected city scores +5; a trend with no posts from that city scores +0.

The city signal is also passed to the LLM prompt as a `City signal:` line (e.g. `"4/17 posts from Shanghai (24%) | Top cities: 上海: 4, 广东: 3"`).

City name mapping (English → Chinese): Shanghai → 上海, Beijing → 北京, Chengdu → 成都, Guangzhou → 广州, Shenzhen → 深圳, Hangzhou → 杭州.

When `city_distribution` is empty, the city signal reads `"No city breakdown available"` and no ranking bonus is applied.

### `assess_confidence()` Thresholds

| Condition | Result |
|---|---|
| `post_count < 3,000` OR `engagement_rate < 0.08` | `LOW` |
| Neither LOW condition triggered, score ≥ 3 | `HIGH` |
| Neither LOW condition triggered, score = 2 | `MEDIUM` |
| Neither LOW condition triggered, score < 2 | `LOW` |

Score increments: `post_count ≥ 5,000` (+1), `engagement_rate ≥ 0.095` (+1), `week_on_week_growth ≥ +20%` (+1), `brand_relevance == "high"` (+1).

All live-scraped cards currently return LOW confidence because the XHS scraper's like-count CSS selector is broken, producing `engagement_rate = 0%`. See DATA_CARD.md constraint 1.

### Data Source Detection

`_detect_data_note()` checks for the presence of `module_1/data/xhs_raw_posts.json` to determine whether the run used live-scraped or synthetic data. This value is stamped into the `CONFIDENCE NOTE` and the card's `**Source:**` header field.

---

## Outputs

### Trend Card Fields (per card in Markdown and HTML)

| Field | Source | Required | Notes |
|---|---|---|---|
| `trend_id` | Module 2 | Required | Section heading: `## t01: Loewe Fashion Highlights` |
| `trend_label` | Module 2 `label` | Required | Human-readable trend name |
| `category` | Module 2 | Optional | May be empty if Module 1 ran without category filter |
| `brand` / `city` | CLI args | Required | Card header: `# CA Trend Brief — Loewe Shanghai` |
| `source` | `load_trends()` | Required | `module_2/output_shortlist.json` (full pipeline) or `Xiaohongshu` (fallback) |
| `week` | `generated_at` from M2 or ISO week | Required | e.g. `2026-03-28` |
| `generated` | Runtime | Required | Timestamp of card generation |
| `model` | `MODEL` env var | Required | OpenRouter model ID used for generation |
| `confidence` | `assess_confidence()` | Required | LOW / MEDIUM / HIGH |
| `trend_overview` | LLM-generated | Required | 2–3 sentences describing the XHS signal |
| `engagement_rate_pct` | Computed from `avg_engagement` | Required | Displayed with benchmark (~4.5%) and sample size |
| `week_on_week_growth` | From `momentum_signal` (M1→M2) or `"+15%"` fallback | Required | Real value from Module 1 date-bucket calculation; fallback for synthetic data only |
| `city_signal` | `_format_city_signal()` | Optional | e.g. `"4/17 posts from Shanghai (24%)"`; `"No city breakdown available"` when absent |
| `confidence_note` | `get_confidence_method()` | Required | Includes threshold values and data source |
| `conversation_starter_zh` | LLM-generated | Required | Chinese-language WeChat-register CA opener |
| `conversation_starter_en` | LLM-generated | Required | English-language CA opener |

### `matched_persona` Block (per card)

Generated by a secondary LLM call (`match_persona_to_trend()`).

| Field | Type | Required | Description |
|---|---|---|---|
| `persona_name` | string | Required | Name of best-fit persona from personas file |
| `persona_summary` | string | Required | Copied verbatim from persona `summary` field |
| `match_rationale` | string | Required | LLM explanation of why trend fits this persona |
| `match_score` | int (1–10) | Required | LLM-assigned strength of match |
| `not_for` | string | Required | Derived from persona `avoid` field |

### File Outputs

| File | Format | Location |
|---|---|---|
| `trend_cards_{brand}_{city}.md` | Markdown | `module_3/trend_brief_agent/` |
| `trend_cards_{brand}_{city}.html` | Styled HTML (self-contained) | `module_3/trend_brief_agent/` |
| `run_log.json` | JSON array of run metadata per card | `module_3/trend_brief_agent/run_log.json` |

---

## Supabase Table Schema

Table name: `trend_cards`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key, auto-generated |
| `run_timestamp` | timestamptz | When the pipeline run executed |
| `brand` | text | e.g. "Dior", "Loewe", "Celine", "Amiri", "Bottega Veneta" |
| `city` | text | e.g. "Shanghai", "Beijing" |
| `model` | text | OpenRouter model ID used |
| `trend_id` | text | From Module 2 output |
| `trend_label` | text | Human-readable trend name |
| `category` | text | "ready-to-wear" or "leather goods" (may be empty for live-scraped runs) |
| `confidence` | text | "LOW", "MEDIUM", or "HIGH" |
| `engagement_rate_pct` | float4 | As a percentage, e.g. 6.2; currently 0.0 for all live-scraped cards |
| `week_on_week_growth` | text | Real value from Module 1 date-bucket calc; "+15%" fallback for synthetic data |
| `city_signal` | text | Formatted city distribution string, e.g. "4/17 posts from Shanghai (24%)" |
| `data_source` | text | "module_2/output_shortlist.json" or "trend_shortlist.json (fallback)" |
| `trend_overview` | text | LLM-generated trend description |
| `confidence_note` | text | Methodology explanation sentence |
| `conversation_starter_zh` | text | Chinese opener |
| `conversation_starter_en` | text | English opener |
| `persona_name` | text | Matched persona name |
| `persona_summary` | text | Persona "who they are" description |
| `match_rationale` | text | LLM match explanation |
| `match_score` | int2 | 1–10 |
| `not_for` | text | Client type to exclude |

---

## What Upstream Modules Need to Provide for Module 3 to Work at Full Quality

Module 3 is complete and handles all current upstream gaps gracefully (fallbacks, skipped checks, LOW confidence flagging). The following changes in upstream modules would unlock MEDIUM/HIGH confidence output and 3–5 cards per brief.

| # | Requirement | Module | Why It Matters for Module 3 |
|---|---|---|---|
| 1 | **Fix the XHS like-count CSS selector** so `likes`, `saves`, `comments` are non-zero on scraped posts | Module 1 (scraper) | `engagement_rate` is currently always 0%, forcing every card to LOW confidence. Fixing this is the single highest-leverage unblock. |
| 2 | **Normalize post date strings to ISO 8601** (e.g. `"03-14 广东"` → `"2026-03-14"`) before writing `xhs_posts.json` | Module 1 (scraper) | Module 2's staleness check currently skips trends with unparseable dates. ISO dates would make the freshness filter accurate, producing a cleaner shortlist. |
| 3 | **Increase scrape volume to ≥200 posts** across 2+ keyword sets or categories | Module 1 (scraper) | More posts → more clusters pass Module 2 threshold → Module 3 receives 3–5 trends per brief instead of 1 |
| 4 | **Set a default category in `run_config.json`** (e.g. `"ready-to-wear"`) | Module 1 (config) | Currently `"category": ""` causes Module 2 to skip brand profile category filtering. Setting a real category restores proper filtering before trends reach Module 3. |
| 5 | **Restore `MIN_TOTAL_ENGAGEMENT = 3,000` in scorer.py** once the scraper is fixed | Module 2 (scorer) | Currently set to 0 for integration testing. Restoring it ensures only trends with real signal reach Module 3. |
