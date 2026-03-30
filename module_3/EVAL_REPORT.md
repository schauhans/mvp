# Module 3 — Evaluation Report

**Run Date:** 2026-03-29
**Evaluator:** `module_3/eval/evaluator.py`
**Full results:** `module_3/eval/eval_results.json`

---

## Dataset

| Field | Value |
|---|---|
| Total cards evaluated | 11 |
| Brand/city runs | Dior Shanghai, Loewe Shanghai, Amiri Shanghai, Bottega Veneta Shanghai, Celine Shanghai |
| Loewe, Celine card source | Full pipeline (live XHS scrape → Module 1 → Module 2 → Module 3) |
| Dior, Amiri, BV card source | Synthetic fallback (Module 3 standalone, no real Module 2 run) |
| Cards per run | Dior: 3, Amiri: 3, BV: 3, Loewe: 1, Celine: 1 |
| Excluded | trend_cards_dior_beijing.md (old format incompatible with evaluator parser) |

---

## Results

| Check | Score | Interpretation |
|---|---|---|
| Check 1 — Metric contextualization rate | **0% pass (0/11 cards)** | Every `Post growth` line fails all three criteria: no benchmark, no sample size, no date. This is a systematic gap in the SYSTEM_PROMPT card template affecting all cards regardless of data source. |
| Check 2 — Conversation starter quality (LLM, 1–5) | **4.36 / 5 avg** | Strong overall. The Loewe full-pipeline card scored **5/5** because its starter directly quoted real scraped post content ("没人能拒绝这条百褶裙", Amazona180). The Celine card scored **4/5** — engaging and persona-aligned but without specific post-language grounding. All synthetic cards scored 4/5. |
| Check 3 — Persona match specificity (LLM, 1–5) | **5.0 / 5 avg** | Perfect score across all 11 cards. Every rationale cited specific aesthetic criteria and included a clear "not for" exclusion. |

---

## Top 5 Failures

Ranked by lowest composite score. All cards fail Check 1; ties broken by C2 + C3.

| Rank | Brand / Trend | Checks Failed | Scores | Reason |
|---|---|---|---|---|
| 1 | **Amiri Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20% (week-on-week)` missing benchmark, sample size, and date. Check 2: "casual tone but slightly structured." |
| 2 | **Amiri Shanghai / Cannage Quilting Detail Focus** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing all context. Check 2: "engaging and personalized but slightly informed in tone." |
| 3 | **Bottega Veneta Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing context. Check 2: "personalized and intimate but slightly structured." |
| 4 | **Bottega Veneta Shanghai / Cannage Quilting Detail Focus** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Week-on-week growth: +20%` missing context. Check 2: "initial reference may come across as slightly abrupt." |
| 5 | **Dior Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing context. Check 2: "personal and engaging but could be slightly more spontaneous." |

---

## Full Pipeline Card Performance

### Loewe Shanghai / Loewe Fashion Highlights (2026-03-28)

| Check | Score | Notes |
|---|---|---|
| Check 1 — Metric context | FAIL | `Post growth: +20% (week-on-week)` — same structural gap as all other cards. Engagement rate shows 0% (real value — scraper CSS selector broken). |
| Check 2 — Starter quality | **5/5** | Highest score in the dataset. Direct quotes from real scraped posts ("没人能拒绝这条百褶裙", Amazona180) made the starter feel genuinely observed rather than generated. |
| Check 3 — Persona specificity | **5/5** | Rationale cited specific products from the trend overview and connected them to the Craft Connoisseur's artisanal orientation. |

**Key finding:** Using real scraped post content as input improved Check 2 quality — the LLM generated a more specific, natural conversation starter when given real post language to draw from, compared to synthetic trend objects.

### Celine Shanghai / Celine Summer Collection Highlights (2026-03-29)

| Check | Score | Notes |
|---|---|---|
| Check 1 — Metric context | FAIL | Same structural gap as all other cards. |
| Check 2 — Starter quality | **4/5** | Persona-aligned and warm, but does not quote specific scraped post language. Unlike Loewe's 5/5 starter, Celine's uses generic descriptors ("minimalist yet structured designs") that could apply to any collection. |
| Check 3 — Persona specificity | **5/5** | The Parisian Minimalist rationale is detailed and exclusion-aware, explicitly flagging clients who favour embellishments. Match score (9/10) adds specificity. |

**Downfalls specific to the Celine run:**
- Only 15 posts scraped — fewer than Loewe (17), both far below the ≥3,000 confidence threshold
- Module 2 fell through to medium-relevance inclusion; card is generated from a below-threshold trend (⚠️ flagged on card)
- Only 1 trend card generated instead of intended 3–5
- Conversation starter does not reference any specific scraped post titles, limiting the "genuinely observed" quality that boosted Loewe's Check 2 to 5/5

---

## One Fix (Module 3)

**Fix the `Post growth` metric line in the SYSTEM_PROMPT card template.**

Currently the template outputs `- Post growth: +[X]% (week-on-week)` with no benchmark, no sample size, and no date — causing Check 1 to fail on every card (100% failure rate). The fix is to update the template to: `- Post growth: +[X]% week-on-week (vs. [N] posts · [month year])`. This forces the LLM to attach the same contextual structure it correctly applies to the engagement rate line, and is the single highest-leverage change available — one prompt edit fixes all cards.

---

## Post-Eval Addition: City Relevance Signal (2026-03-29)

After this evaluation batch was run, city relevance detection was added to the Module 3 pipeline. This is not reflected in the scores above.

**What was added in Module 3:**
- `compute_composite_score()` adds up to +5 ranking points for trends where the selected city has a high share of geolocated posts in `city_distribution`
- A `City signal:` line is injected into the LLM card prompt so the model can reference local traction
- `_format_city_signal()` formats the distribution for display (e.g. `"4/17 posts from Shanghai (24%) | Top cities: 上海: 4, 广东: 3"`)

**Current limitation:** The evaluation batch used synthetic data (Dior/Amiri/BV) and live-scraped runs where the engagement CSS selector returned 0. Neither source produced meaningful `city_distribution` data, so the city signal line reads `"No city breakdown available"` for all current cards and no ranking boost applies. A future eval run on a full live scrape with working engagement extraction is needed to assess this feature.

---

## What Upstream Modules Need to Fix for Eval Scores to Improve

The failures above are a mix of Module 3 prompt gaps (Check 1 — fixable next week) and upstream data quality issues that limit what Module 3 can produce. The following upstream changes would directly improve evaluation scores:

| # | What Needs to Change | Module | Expected Eval Impact |
|---|---|---|---|
| 1 | **Fix the XHS like-count CSS selector** | Module 1 (scraper) | Engagement rate goes from 0% to real values → Check 1 contextualization improves, confidence ratings unlock MEDIUM/HIGH |
| 2 | **Normalize post date strings to ISO 8601** | Module 1 (scraper) | Module 2 staleness check becomes accurate → cleaner trend shortlist → better card quality overall |
| 3 | **Increase scrape volume to ≥200 posts** across 2+ keyword sets | Module 1 (scraper) | More trends reach Module 2 threshold → 3–5 cards per brief → Check 2 and Check 3 can be assessed across a full brief rather than a single card |
| 4 | **Set a real default category in `run_config.json`** | Module 1 (config) | Brand profile category filtering restored → more relevant trends reach Module 3 |
| 5 | **Restore `MIN_TOTAL_ENGAGEMENT = 3,000` in scorer.py** | Module 2 (scorer) | Noise filtered before reaching Module 3 → higher-signal cards |
