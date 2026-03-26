# IO_CONTRACT.md — Module 2: Trend Relevance & Materiality Filter Agent

## Overview

This document defines the exact input and output contract for Module 2. All upstream and downstream modules must conform to this schema.

---

## INPUT — Trend Objects (from Module 1)

**File:** `data/trend_objects.json`
**Produced by:** Module 1 — XHS Trend Object Builder
**Format:** JSON object with a `trend_objects` array

### Top-Level Envelope

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_id` | string | Yes | Unique identifier for the Module 1 extraction run |
| `brand` | string | Yes | Brand scope of the run (e.g. "ALL") |
| `category` | string | Yes | Primary category of the run |
| `trend_objects` | array | Yes | Array of individual trend objects |

### Trend Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trend_id` | string | Yes | Unique identifier (e.g. "t01") |
| `label` | string | Yes | Short trend name — used in taboo screening and output |
| `category` | string | Yes | Product category — must match `active_categories` in brand profile |
| `summary` | string | Yes | 1-3 sentence description — used in taboo screening and LLM context |
| `ai_reasoning` | string | No | Module 1's reasoning — passed to LLM as additional context |
| `confidence` | string | No | Module 1 confidence level: "high", "medium", "low" |
| `labeling_source` | string | No | How Module 1 labeled it: "heuristic", "llm", etc. |
| `evidence.post_ids` | array[string] | Yes | List of post IDs supporting this trend |
| `evidence.snippets` | array[string] | Yes | Chinese-language text snippets — minimum 2 required by pre-filter |
| `evidence.posts` | array[object] | Yes | Individual post objects with engagement data |
| `evidence.posts[].post_id` | string | Yes | Unique post ID |
| `evidence.posts[].title` | string | No | Post title |
| `evidence.posts[].date` | string | Yes | ISO 8601 date or datetime (e.g. "2026-03-18") — used for freshness check |
| `evidence.posts[].brand` | string | No | Brand referenced in post |
| `evidence.posts[].likes` | number | No | Like count |
| `evidence.posts[].comments` | number | No | Comment count |
| `evidence.posts[].saves` | number | No | Save count |
| `evidence.posts[].creator` | string | No | Creator handle — used by LLM for brand-fit assessment |
| `metrics.post_count` | number | Yes | Total number of posts in this cluster |
| `metrics.total_engagement` | number | Yes | Sum of all likes + comments + saves |
| `metrics.avg_engagement` | number | No | Average engagement per post |
| `metrics.total_likes` | number | No | Sum of likes |
| `metrics.total_comments` | number | No | Sum of comments |
| `metrics.total_saves` | number | No | Sum of saves |
| `metrics.top_keywords` | array[string] | No | Extracted keywords from posts |
| `timestamp` | string | No | ISO 8601 datetime when Module 1 created this object |

### Pre-Filter Hard Requirements

Module 2 will **automatically reject** a trend (without LLM call) if ANY of the following are true:

1. `category` not in `brand_profile.active_categories`
2. `metrics.post_count` < 5
3. `metrics.total_engagement` < 3000
4. Most recent date in `evidence.posts[].date` is before 2026-03-04 (>21 days before 2026-03-25)
5. `evidence.snippets` has fewer than 2 items
6. Any `brand_taboos` keyword appears (case-insensitive) in `label` or `summary`

---

## OUTPUT — Shortlisted Trends

**File:** `outputs/output_shortlist.json`
**Consumed by:** Module 3 (reporting), Module 4 (clienteling)

### Top-Level Envelope

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Module 2 run ID (e.g. "run_0001_m2") |
| `generated_at` | string | ISO 8601 datetime of this run |
| `brand` | string | Brand evaluated (e.g. "Christian Dior") |
| `module1_run_id` | string | The Module 1 run this input came from |
| `total_evaluated` | number | Total trend objects received from Module 1 |
| `total_prefilter_rejected` | number | Trends rejected by deterministic pre-filter |
| `total_shortlisted` | number | Trends in the final shortlist |
| `shortlist` | array | Array of shortlisted trend objects (max 5) |

### Shortlist Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `rank` | number | Rank by composite_score (1 = highest) |
| `trend_id` | string | Original trend_id from Module 1 |
| `label` | string | Trend name from Module 1 |
| `category` | string | Product category |
| `composite_score` | number | Weighted average score (0–10) |
| `scores.freshness` | number | LLM freshness score (0–10) |
| `scores.brand_fit` | number | LLM brand fit score (0–10) |
| `scores.category_fit` | number | LLM category fit score (0–10) |
| `scores.materiality` | number | LLM materiality score (0–10) |
| `scores.actionability` | number | LLM actionability score (0–10) |
| `confidence` | string | LLM confidence: "high", "medium", "low" |
| `why_selected` | string | 3-5 sentence evidence-grounded reasoning |
| `evidence_references` | array[string] | Direct quotes or metrics cited by LLM |
| `metric_signal.total_engagement` | number | From original metrics |
| `metric_signal.post_count` | number | From original metrics |
| `metric_signal.avg_engagement` | number | From original metrics |
| `disqualifying_reason` | null | Always null for shortlisted items |

### Score Weights

```
composite_score = (freshness × 0.20) + (brand_fit × 0.30) + (category_fit × 0.20)
                + (materiality × 0.15) + (actionability × 0.15)
```

**Minimum thresholds for shortlisting:**
- `composite_score` ≥ 6.5
- No individual dimension score < 4
- LLM `shortlist` judgment = true

### Run Log

**File:** `outputs/run_log.json`
Contains full audit trail including all LLM evaluations, pre-filter rejections, and shortlist IDs.

---

## Assumptions

1. **Brand profile must be present** — `brand_profile.json` must exist and contain `active_categories`, `brand_taboos`, and `clientele` fields before the agent can run.

2. **Dates must be ISO 8601** — All `evidence.posts[].date` values must be parseable as ISO 8601 date or datetime strings. Invalid dates cause the trend to be rejected at pre-filter with a "no valid post dates" reason.

3. **Category must match active_categories** — Trends with categories not in `brand_profile.active_categories` are rejected immediately. For this run, only "ready-to-wear" and "leather goods" are active.

4. **No cross-platform identity matching** — Creator handles are used only for brand-fit qualitative assessment. No cross-platform identity resolution is performed. In production, commenter IDs would be SHA-256 hashed.

5. **Synthetic data note** — The current dataset is fully synthetic (see DATA_CARD.md). Real Module 1 output is targeted for Week 11. Schema is identical to production Module 1 output.

6. **Max shortlist is 5** — Module 2 will never output more than 5 trends. If fewer than 5 pass all criteria, only the passing trends are output. The shortlist is never padded.
