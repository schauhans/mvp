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
| `evidence_references` | string[] | Optional | `evidence_references[0]` → `top_post_example`; `[1:]` → `trending_hashtags` |
| `metric_signal.post_count` | int | Required | `assess_confidence()` threshold check; DATA SIGNAL display |
| `metric_signal.avg_engagement` | float | Required | Converted to `engagement_rate` via `min(avg_engagement / 10000, 1.0)` |
| `brand` | string | Required | Brand check — if this doesn't match the current run's brand, the cache is skipped |

| `city_distribution` | dict | Optional | e.g. `{"上海": 4, "广东": 3}` — extracted by Module 1 from post date strings; passed through Module 2 unchanged; used by Module 3 for city relevance ranking and card display |

**Fields NOT passed from Module 2:**
- `city` — Module 2 does not attach a city. Module 3 stamps the user-selected city onto all trends at runtime via `select_trends()`. Trends with `city=None` are treated as city-agnostic and included in any city run. City relevance is surfaced instead via `city_distribution`.
- `week_on_week_growth` — Module 2 does not output WoW growth. Module 3 hardcodes `"+20%"` for all Module 2 shortlist items in `normalise_from_module2()`.

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
| `--brand` | Required | Brand name passed from `main.py`; used for brand cache check and persona file selection |
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

`compute_composite_score()` now accepts the selected city and applies a bonus of up to +5 points based on `city_distribution`. A trend where 100% of geolocated posts are from the selected city scores +5; a trend with no posts from that city scores +0. This means trends with strong local signal rise above equally-scored national trends when ranking the final shortlist.

The city relevance signal is also passed to the LLM prompt as a `City signal:` line (e.g. `"4/17 posts from Shanghai (24%) | Top cities: 上海: 4, 广东: 3"`) so the LLM can reference local traction in the card text.

City name mapping used (English → Chinese): Shanghai → 上海, Beijing → 北京, Chengdu → 成都, Guangzhou → 广州, Shenzhen → 深圳, Hangzhou → 杭州. Cities not in this map fall back to the raw string.

When `city_distribution` is empty (e.g. engagement data not captured, or synthetic fallback), the city signal line reads `"No city breakdown available"` and no ranking bonus is applied.

### `assess_confidence()` Thresholds

| Condition | Result |
|---|---|
| `post_count < 3,000` OR `engagement_rate < 0.08` | `LOW` |
| Neither LOW condition triggered, score ≥ 3 | `HIGH` |
| Neither LOW condition triggered, score 2 | `MEDIUM` |
| Neither LOW condition triggered, score < 2 | `LOW` |

Score increments: `post_count ≥ 5,000` (+1), `engagement_rate ≥ 0.095` (+1), `week_on_week_growth ≥ +20%` (+1), `brand_relevance == "high"` (+1).

**Note:** All live-scraped cards currently return LOW confidence because the XHS scraper's `.like-wrapper` CSS selector no longer returns like counts, producing `engagement_rate = 0%`. See DATA_CARD.md constraint 1.

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
| `week` | `generated_at` from M2 or ISO week | Required | e.g. `2026-03-28` or `2026-W12` |
| `generated` | Runtime | Required | Timestamp of card generation |
| `model` | `MODEL` env var | Required | OpenRouter model ID used for generation |
| `confidence` | `assess_confidence()` | Required | LOW / MEDIUM / HIGH |
| `trend_overview` | LLM-generated | Required | 2–3 sentences describing the XHS signal |
| `engagement_rate_pct` | Computed from `avg_engagement` | Required | Displayed with benchmark (~4.5%) and sample size |
| `week_on_week_growth` | Hardcoded `+20%` (M2 path) | Required | Module 2 does not output WoW growth |
| `city_signal` | `_format_city_signal()` | Optional | e.g. `"4/17 posts from Shanghai (24%) | Top cities: 上海: 4, 广东: 3"`; `"No city breakdown available"` when data absent |
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

## Module 2 Contract Changes (2026-03-29)

Module 2's `agent.py` now accepts a `--brand` CLI argument passed from `main.py`. This replaced the previous behaviour where `BRAND` was read only from the `BRAND` env var, which always resolved to the `.env` default regardless of what brand the user entered at the `main.py` prompt. The `--brand` arg takes priority over the env var.

Module 2's `evaluator.py` now applies the same `/` check as all other modules: if `DEFAULT_MODEL` does not contain `/`, it falls back to `openai/gpt-4o-mini`. This prevents 400 errors when `DEFAULT_MODEL` is set to a bare Anthropic model ID.

---

## Supabase Table Schema

Table name: `trend_cards`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key, auto-generated |
| `run_timestamp` | timestamptz | When the pipeline run executed |
| `brand` | text | e.g. "Dior", "Loewe" |
| `city` | text | e.g. "Shanghai", "Beijing" |
| `model` | text | OpenRouter model ID used |
| `trend_id` | text | From Module 2 output |
| `trend_label` | text | Human-readable trend name |
| `category` | text | "ready-to-wear" or "leather goods" (may be empty for live-scraped runs) |
| `confidence` | text | "LOW", "MEDIUM", or "HIGH" |
| `engagement_rate_pct` | float4 | As a percentage, e.g. 6.2; currently 0.0 for all live-scraped cards |
| `week_on_week_growth` | text | Hardcoded "+20%" for Module 2 path |
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
