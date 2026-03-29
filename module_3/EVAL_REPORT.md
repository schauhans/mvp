# Module 3 — Evaluation Report

**Run Date:** 2026-03-29
**Evaluator:** `module_3/eval/evaluator.py`
**Full results:** `module_3/eval/eval_results.json`

---

## Dataset

| Field | Value |
|---|---|
| Total cards evaluated | 10 |
| Brand/city runs | Dior Shanghai, Loewe Shanghai, Amiri Shanghai, Bottega Veneta Shanghai |
| Loewe card source | Full pipeline (live XHS scrape → Module 1 → Module 2 → Module 3) |
| Dior, Amiri, BV card source | Synthetic fallback (Module 3 only, no Module 2 run) |
| Cards per run | Dior: 3, Amiri: 3, BV: 3, Loewe: 1 (only 1 trend passed Module 2 threshold) |
| Excluded | trend_cards_dior_beijing.md (old format with MAISON LENS / CA USAGE NOTE sections) |

---

## Results

| Check | Score | Interpretation |
|---|---|---|
| Check 1 — Metric contextualization rate | **0% pass (0/10 cards)** | Every `Post growth` line fails all three criteria — no benchmark, no sample size, no date. This is a systematic prompt gap in the SYSTEM_PROMPT card template, affecting all cards regardless of data source. The Loewe full-pipeline card is no exception: it displays `Post growth: +20% (week-on-week)` with no context, identical to the synthetic cards. |
| Check 2 — Conversation starter quality (LLM, 1–5) | **4.4 / 5 avg** | Strong overall. The new Loewe full-pipeline card scored **5/5** — the highest possible — because its starter directly quoted real scraped post content ("没人能拒绝这条百褶裙", Amazona180), making it feel genuinely observed rather than generated. Cards scoring 4/5 were judged "personal and engaging but slightly structured." |
| Check 3 — Persona match specificity (LLM, 1–5) | **5.0 / 5 avg** | Perfect score across all 10 cards. The Loewe full-pipeline card cited specific product names from the scraped posts (Amazona180, pleated skirts) and connected them directly to the Craft Connoisseur persona's artisanal orientation. |

---

## Top 5 Failures

Ranked by lowest composite score. All cards fail Check 1; ties broken by C2+C3.

| Rank | Brand / Trend | Checks Failed | Scores | Reason |
|---|---|---|---|---|
| 1 | **Amiri Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20% (week-on-week)` missing benchmark, sample size, date. Check 2: "casual tone but slightly structured." |
| 2 | **Amiri Shanghai / Cannage Quilting Detail Focus** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing all context. Check 2: "engaging and personalized but slightly informed in tone." |
| 3 | **Bottega Veneta Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing context. Check 2: "personalized and intimate but slightly structured." |
| 4 | **Bottega Veneta Shanghai / Cannage Quilting Detail Focus** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Week-on-week growth: +20%` missing context. Check 2: "initial reference may come across as slightly abrupt." |
| 5 | **Dior Shanghai / Top Handle Bag Elegance** | Check 1 + Check 2 | C1: FAIL · C2: 4/5 · C3: 5/5 | `Post growth: +20%` missing context. Check 2: "personal and engaging but could be slightly more spontaneous." |

---

## Full Pipeline Card Performance (Loewe Shanghai / Loewe Fashion Highlights)

The only card generated through the complete M1 → M2 → M3 pipeline using real scraped data.

| Check | Score | Notes |
|---|---|---|
| Check 1 — Metric context | FAIL | `Post growth: +20% (week-on-week)` — same structural gap as all other cards. Engagement rate shows 0% (real value — scraper CSS selector broken). |
| Check 2 — Starter quality | **5/5** | Highest score in the dataset. Direct quotes from real scraped posts ("没人能拒绝这条百褶裙", Amazona180) made the starter feel genuinely observed. |
| Check 3 — Persona specificity | **5/5** | Rationale cited specific products from the trend overview and connected them to the Craft Connoisseur's artisanal orientation. |

**Key finding:** Using real scraped post content as input improved Check 2 quality — the LLM generated a more specific, natural conversation starter when given real post language to draw from, compared to synthetic trend objects.

---

## One Fix

**Fix the `Post growth` metric line in the SYSTEM_PROMPT card template.**

Currently the template outputs `- Post growth: +[X]% (week-on-week)` with no benchmark, no sample size, and no date — causing Check 1 to fail on every card (100% failure rate across all 10). The fix is to update the template to: `- Post growth: +[X]% week-on-week (vs. [N] posts · [month year])`. This forces the LLM to attach the same contextual structure it correctly applies to the engagement rate line, and is the single highest-leverage change available — one prompt edit fixes all cards.

---

## Post-Eval Change: City Relevance Signal (2026-03-29)

After this evaluation batch was run, city relevance detection was added to the pipeline. This change is not reflected in the eval scores above but is documented here for completeness.

**What changed across all three modules:**

- **Module 1** — `build_trend_object()` now scans all post date strings in each cluster for known Chinese city/province names (e.g. `"03-14 上海"`, `"昨天 广东"`) and adds `metrics.city_distribution: {"上海": 4, "广东": 3, ...}` to each trend object.
- **Module 2** — `convert_to_module3_format()` passes `city_distribution` through to `trend_shortlist.json` unchanged.
- **Module 3** — three effects: (1) `compute_composite_score()` adds up to +5 ranking points for trends where the selected city has a high share of geolocated posts; (2) a `City signal:` line is injected into the LLM card prompt so the model can reference local traction; (3) `_format_city_signal()` formats the distribution for display (e.g. `"4/17 posts from Shanghai (24%) | Top cities: 上海: 4, 广东: 3"`).

**Evaluation implication:** The current eval batch used synthetic data (Dior/Amiri/BV) and a live-scraped Loewe run where the CSS selector returned 0 engagement. Neither source produced meaningful `city_distribution` data, so the city signal line will read `"No city breakdown available"` for all current batch cards and no ranking boost will apply. A future eval run on a full live scrape with working engagement extraction would be needed to assess whether city-boosted ranking produces meaningfully different card selection or LLM output quality.
