# Module 3 — Data Card

## Data Sources

**Input trend objects:**
Module 3 reads from two possible sources, in priority order:

1. `module_2/outputs/output_shortlist.json` — the ranked shortlist produced by Module 2's two-stage filter (deterministic pre-filter + LLM evaluation via OpenRouter). Used when the full pipeline (`python main.py`) has been run for the same brand.
2. `module_3/trend_brief_agent/trend_shortlist.json` — fallback file for standalone testing. Used when Module 2 output is absent or brand-mismatched.

**Brand profiles used:** `module_2/brand_profile_{brand}.json`
- Dior, Loewe, Amiri, Bottega Veneta, Celine

**Persona files used:** `module_3/trend_brief_agent/personas/{brand}_personas.json`
- 5 personas each for: Dior, Loewe, Amiri, Bottega Veneta, Celine

---

## Date Range

Prototype runs: 2026-03-25 through 2026-03-28
Full pipeline runs (live scrape → M1 → M2 → M3): 2026-03-28 (Loewe), 2026-03-29 (Celine)

---

## Volume (evaluation batch)

| Brand | City | Cards | Data Source | Pipeline Stage |
|---|---|---|---|---|
| Dior | Shanghai | 3 | Synthetic fallback | M3 only |
| Loewe | Shanghai | 1 | Live XHS scrape → M1 → M2 → M3 | Full pipeline ✓ |
| Amiri | Shanghai | 3 | Synthetic fallback | M3 only |
| Bottega Veneta | Shanghai | 3 | Synthetic fallback | M3 only |
| Celine | Shanghai | 1 | Live XHS scrape → M1 → M2 → M3 | Full pipeline ✓ |

**Total evaluated: 11 cards across 5 brand/city runs**

Note: Dior Beijing excluded from evaluation batch (old card format incompatible with evaluator parser).

---

## Real vs Synthetic

### Dior Shanghai, Amiri Shanghai, Bottega Veneta Shanghai — Synthetic (M3 fallback only)

Generated from the generic `trend_shortlist.json` fallback. Module 2 was not run for these brands in this batch.

| Data Element | Status | Notes |
|---|---|---|
| XHS post content | **Synthetic** | 30 manually authored posts in `module_1/data/xhs_posts.json` |
| Post engagement metrics | **Synthetic** | All zeros |
| Trend labels | **Synthetic** | Generic luxury trends from fallback file |
| Engagement rate benchmark (~4.5%) | **Estimated** | Industry-level estimate, not from XHS API |
| Week-on-week growth (+20%) | **Placeholder** | Hardcoded default in `normalise_from_fallback()` |
| Brand profile / persona files | **Authored** | Written from public brand positioning; not validated with live CRM data |
| LLM-generated card text | AI-generated | OpenRouter `openai/gpt-4o-mini` |
| Confidence ratings | **LOW** | Post count far below ≥3,000 threshold |

### Loewe Shanghai — Full Pipeline (M1 → M2 → M3), 2026-03-28

| Data Element | Status | Notes |
|---|---|---|
| XHS post titles | **Real** | 40 posts scraped live from XHS via DrissionPage |
| Post dates | **Real** | Chinese-locale strings (e.g. `"03-14 广东"`) — not ISO-parseable |
| Likes / saves / comments | **Zero** | CSS selector failure — XHS HTML changed since scraper was built |
| Engagement rate on card | **0%** | Direct result of zero likes; not a pipeline error |
| Module 1 clustering | **Real** | LLM clustered real Loewe post titles |
| Module 2 scoring | **Real** | Loewe brand profile applied; shortlisted at composite score 7.65 |
| Source field | **Real** | `module_2/output_shortlist.json` — confirmed M3 read from real M2 output |
| Persona matching | **Real** | The Craft Connoisseur matched from `loewe_personas.json` |
| Conversation starter | **Real** | References specific scraped post content ("没人能拒绝这条百褶裙", Amazona180) |
| Confidence rating | **LOW** | 17 posts, 0% engagement — correctly flagged below thresholds |

### Celine Shanghai — Full Pipeline (M1 → M2 → M3), 2026-03-29

| Data Element | Status | Notes |
|---|---|---|
| XHS post titles | **Real** | 15 posts scraped live from XHS |
| Likes / saves / comments | **Zero** | Same CSS selector failure as Loewe |
| Engagement rate on card | **0%** | Real value — scraper limitation, not a pipeline error |
| Module 1 clustering | **Real** | LLM clustered real Celine post titles → "Celine Summer Collection Highlights" |
| Module 2 scoring | **Real** | Celine brand profile applied; fell back to medium-relevance inclusion (fewer than 3 high-relevance trends) |
| Source field | **Real** | `module_2/output_shortlist.json` |
| Persona matching | **Real** | The Parisian Minimalist matched from `celine_personas.json` |
| Confidence rating | **LOW** | 15 posts, 0% engagement — correctly flagged |

**Known downfalls specific to the Celine run:**
- Only 15 posts — far below the ≥3,000 confidence threshold
- Only 1 trend card generated instead of the intended 3–5
- Conversation starter does not quote specific scraped post language, reducing observed-vs-generated quality

---

## Known Constraints

1. **Engagement data unavailable.** The XHS scraper's CSS selector for like counts is broken. All scraped posts have `likes=0`, producing 0% engagement rate on all live-scraped cards. Cards are pipeline-verified but engagement-unvalidated.
2. **Post counts are too low for MEDIUM/HIGH confidence.** A single scraping session yields ~15–40 posts per brand. Far below the ≥3,000 threshold. All live-scraped cards are flagged LOW.
3. **Only one trend shortlisted per full-pipeline run.** With thin data and 0 engagement, only one trend per brand passes Module 2's composite threshold (6.5). Cards are generated from a single-trend shortlist rather than the intended 3–5.
4. **Persona files are prototypes.** Not validated against real client CRM data or CA interviews.
5. **Engagement rate is an approximation.** Computed as `avg(total interactions per post) / 10,000`. XHS does not expose impressions, so true engagement rate (interactions/reach) is unavailable.
6. **Week-on-week growth is hardcoded for synthetic data.** `+20%` is a default for the fallback path. Full-pipeline runs use real `momentum_signal` from Module 1 date-bucket calculation.
7. **Single city per run.** City is stamped by the user at Module 3 runtime; Module 2 does not output a city field.

---

## What Needs to Change in Upstream Modules for Module 3 to Work at Full Quality

These are not Module 3 issues — Module 3 handles them gracefully — but fixing them upstream would unlock MEDIUM/HIGH confidence cards and 3–5 trends per brief instead of 1.

| # | What Needs to Change | Module | Impact on Module 3 |
|---|---|---|---|
| 1 | **Fix the XHS like-count CSS selector.** The `.like-wrapper` selector no longer returns likes from search result pages since an XHS HTML update. All scraped posts come in with `likes=0`, which propagates to 0% engagement on every card. | Module 1 (scraper) | Unlocks real engagement rates → MEDIUM/HIGH confidence cards become possible |
| 2 | **Normalize post date strings to ISO format.** Live XHS dates come in as Chinese-locale strings (e.g. `"03-14 广东"`, `"昨天 14:57"`). Module 2's staleness check currently skips trends where no ISO date is found rather than rejecting them. Real date parsing would make the freshness filter accurate. | Module 1 (scraper) | More accurate trend filtering in Module 2 → better-quality shortlist reaching M3 |
| 3 | **Increase scrape volume to ≥200 posts across 2+ keyword sets or categories.** Current sessions yield ~15–40 posts per brand. Module 2's minimum engagement threshold (`MIN_TOTAL_ENGAGEMENT`) is currently set to 0 for integration testing — it should be restored to 3,000 once the scraper captures real like counts, at which point post volume becomes essential. | Module 1 (scraper) | More clusters pass M2 threshold → 3–5 trend cards per brief instead of 1 |
| 4 | **Restore `MIN_TOTAL_ENGAGEMENT = 3,000` in Module 2 pre-filter.** This was lowered to 0 to allow integration testing with broken engagement data. It should be restored once the scraper is fixed. | Module 2 (scorer) | Ensures only trends with real signal reach Module 3 |
| 5 | **Set a default category in Module 1 run config.** Live scrapes currently produce trends with an empty `category` field because `run_config.json` has `"category": ""`. Module 2 skips the category check when category is empty, which means all trends pass regardless of category fit. Setting a real category (e.g. `"ready-to-wear"`) would restore proper brand profile filtering. | Module 1 (config) | Tighter relevance filtering before cards are generated |
