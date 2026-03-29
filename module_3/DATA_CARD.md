# Module 3 — Data Card

## Data Sources

**Input trend objects:**
Module 3 reads from two possible sources, in priority order:

1. `module_2/outputs/output_shortlist.json` — the ranked shortlist produced by Module 2's two-stage filter (deterministic pre-filter + LLM evaluation via OpenRouter). Used when the full pipeline (`python main.py`) has been run successfully.
2. `module_3/trend_brief_agent/trend_shortlist.json` — fallback file written by Module 2 in a Module 3-compatible schema. Used when Module 2 produces an empty shortlist or the pipeline has not been run.

**Brand profiles used:** `module_2/brand_profile_{brand}.json`
- Dior: `brand_profile.json` (original class file)
- Loewe: `brand_profile_loewe.json`
- Amiri: `brand_profile_amiri.json`
- Bottega Veneta: `brand_profile_bottega_veneta.json`

**Persona files used:** `module_3/trend_brief_agent/personas/{brand}_personas.json`
- `dior_personas.json` — 5 personas
- `loewe_personas.json` — 5 personas
- `amiri_personas.json` — 5 personas
- `bottega_veneta_personas.json` — 5 personas

---

## Date Range

Prototype runs: 2026-03-25 through 2026-03-28
Full pipeline run (Loewe, live scrape → M1 → M2 → M3): 2026-03-28 to 2026-03-29

---

## Volume (evaluation batch)

| Brand | City | Cards | Data Source | Pipeline Stage |
|---|---|---|---|---|
| Dior | Shanghai | 3 | Synthetic fallback | M3 only |
| Loewe | Shanghai | 1 | Live XHS scrape → M1 → M2 → M3 | Full pipeline ✓ |
| Amiri | Shanghai | 3 | Synthetic fallback | M3 only |
| Bottega Veneta | Shanghai | 3 | Synthetic fallback | M3 only |

**Total evaluated: 10 cards across 4 brand/city runs**

Note: Dior Beijing excluded from evaluation batch (old card format with MAISON LENS / CA USAGE NOTE sections incompatible with evaluator parser).

---

## Real vs Synthetic

### Dior Shanghai, Amiri Shanghai, Bottega Veneta Shanghai — Synthetic (M3 fallback only)

Generated from the generic `trend_shortlist.json` fallback before full pipeline integration was complete. Module 2 was not run for these brands in this batch.

| Data Element | Status | Notes |
|---|---|---|
| XHS post content | **Synthetic** | 30 manually authored posts in `module_1/data/xhs_posts.json` |
| Post engagement metrics | **Synthetic** | All zeros; detail-page scraping not used |
| Trend labels | **Synthetic** | Generic luxury trends from fallback file (e.g. "Top Handle Bag Elegance", "Lady Dior Styling") |
| Engagement rate benchmark (~4.5%) | **Estimated** | Industry-level estimate, not from XHS API |
| Week-on-week growth (+20%) | **Placeholder** | Hardcoded default in `normalise_from_module2()` |
| Brand profile / persona files | **Authored** | Written from public brand positioning; not validated with live CRM data |
| LLM-generated card text | AI-generated | OpenRouter `openai/gpt-4o-mini` output |
| Confidence ratings | **LOW** | `assess_confidence()` — post_count far below ≥3,000 threshold |

### Loewe Shanghai — Full Pipeline (M1 → M2 → M3), 2026-03-28

The only card in this batch generated through the complete Modules 1 → 2 → 3 pipeline using live-scraped XHS data.

| Data Element | Status | Notes |
|---|---|---|
| XHS post titles | **Real** | 40 posts scraped live from XHS via DrissionPage (Loewe keywords) |
| Post dates | **Real** | Chinese-locale strings (e.g. `"03-14 广东"`, `"昨天 14:57"`) — not ISO-parseable |
| Likes / saves / comments | **Zero** | `.like-wrapper` CSS selector returned empty counts (XHS HTML change since scraper was built) |
| Engagement rate on card | **0%** | Direct result of zero likes; not a pipeline error |
| Module 1 clustering | **Real** | LLM (`openai/gpt-4o-mini`) clustered real Loewe post titles → "Loewe Fashion Highlights", "LOEWE Spring/Summer 2026" |
| Module 2 scoring | **Real** | Loewe brand profile applied; "Loewe Fashion Highlights" shortlisted at composite score 7.65 |
| Source field on card | **Real** | `module_2/output_shortlist.json` — confirms M3 read from real M2 output, not fallback |
| Persona matching | **Real** | The Craft Connoisseur matched from `loewe_personas.json` |
| Conversation starter | **Real** | References specific scraped post content ("没人能拒绝这条百褶裙", Amazona180) |
| Confidence rating | **LOW** | 17 posts, 0% engagement — correctly flagged below thresholds |

---

## Pipeline Integration Blockers Removed for Testing

Several pre-filter rules in Module 2 and LLM calls in Module 1 blocked the full pipeline from running during development. These were bypassed for integration testing and are documented here. Each should be addressed before production use.

| # | Blocker | Module | Change Made | Production Fix Needed |
|---|---|---|---|---|
| 1 | `MIN_TOTAL_ENGAGEMENT = 3000` rejected all live-scraped trends because `.like-wrapper` CSS selector returns 0 likes (XHS HTML change) | `module_2/scorer.py` | Lowered to `0` | Restore to 3,000 once scraper CSS selector is fixed to capture real like counts |
| 2 | Staleness check: `_get_last_post_date()` returned `None` for Chinese-locale date strings (e.g. `"03-14 广东"`), causing `"No valid post dates found"` rejection | `module_2/scorer.py` | Changed to skip rejection (assume fresh) when no ISO date is parseable | Normalize XHS date strings to ISO format in the scraper before writing `xhs_posts.json` |
| 3 | Module 1 used `client.responses.create()` (OpenAI Responses API) — not supported by OpenRouter, silently fell back to heuristic labels ("Mixed Beauty Trend Signals") | `module_1/xhs_trend_builder.py` | Switched to `client.chat.completions.create()` | Permanent fix — already applied |
| 4 | Model ID `claude-haiku-4-5-20251001` (bare Anthropic format) was passed to OpenRouter, which requires `"provider/model"` format — caused 400 errors in all three modules | M1, M2, M3 | Added `/` check in each module: if no `/` in model string, fall back to `openai/gpt-4o-mini` | Permanent fix — already applied. Long-term: set `DEFAULT_MODEL=openai/gpt-4o-mini` in `.env` |
| 5 | Module 2 pre-filter Rule 1 rejected trends with empty `category` field — Module 1 sets category from `run_config.json` which had `"category": ""` | `module_2/scorer.py` | Changed to skip category check when category is empty string | Set a default category in Module 1 config, or have Module 2 infer category from trend label |
| 6 | Module 3 loaded stale Dior `output_shortlist.json` for Loewe runs — no brand check before consuming Module 2 cache | `module_3/trend_brief_agent/agent.py` | Added brand slug comparison before loading cache | Permanent fix — already applied |

---

## Known Constraints

1. **Engagement data unavailable from current scraper.** The `.like-wrapper` CSS selector no longer returns like counts from XHS search result pages. All scraped posts have `likes=0`, making engagement rate 0% on all live-scraped cards. Cards are pipeline-verified but engagement-unvalidated.
2. **Post counts are LOW confidence.** A single scraping session yields ~40 posts total across all keywords. This produces clusters of 10–20 posts, far below the ≥3,000 threshold needed for MEDIUM/HIGH confidence. All live-scraped cards are flagged LOW.
3. **Only one trend shortlisted per full-pipeline run.** With 40 posts and 0 engagement, Module 2's LLM materiality scores are low. Only one of two clusters passed the composite threshold (6.5). Cards are generated from a single-trend shortlist rather than the intended 3–5.
4. **Persona files are prototypes.** Not validated against real client CRM data or CA interviews.
5. **Engagement rate is an approximation.** Computed as `avg(total interactions per post) / 10,000`. XHS does not expose impressions, so true engagement rate (interactions/reach) is unavailable.
6. **Week-on-week growth is hardcoded.** Module 2 does not output WoW growth; `+20%` is a default for shortlisted trends.
7. **Single city per run.** Module 2 does not attach a city field to trends; city is stamped by the user at Module 3 runtime.
