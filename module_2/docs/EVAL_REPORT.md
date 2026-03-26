# EVAL_REPORT.md — Module 2: Trend Relevance & Materiality Filter Agent

> **Status:** Completed — based on actual run on 2026-03-25 with 30 synthetic trend objects.

---

## Run Information

| Field | Value |
|-------|-------|
| **Run date** | 2026-03-25 |
| **Run ID** | run_0001_m2 |
| **Dataset** | Synthetic — 30 trend objects (see DATA_CARD.md) |
| **Brand** | Christian Dior |
| **Categories** | ready-to-wear, leather goods |
| **Model** | claude-sonnet-4-20250514 |

---

## Dataset Summary

| Metric | Count |
|--------|-------|
| Total trend objects input | 30 |
| Pre-filter rejected | 15 |
| Passed to LLM evaluation | 15 |
| LLM evaluated | 15 |
| Final shortlist | 5 |

---

## Final Shortlist

| Rank | Trend ID | Label | Category | Composite Score | Confidence |
|------|----------|-------|----------|-----------------|------------|
| 1 | t20 | Lady Dior Styling and Heritage | leather goods | 9.00 | high |
| 2 | t04 | New Bar Jacket Reinterpretation | ready-to-wear | 8.80 | high |
| 3 | t18 | Top Handle Bag Elegance | leather goods | 8.80 | high |
| 4 | t19 | Cannage Quilting Detail Focus | leather goods | 8.80 | high |
| 5 | t01 | Soft Tailoring Revival | ready-to-wear | 8.60 | high |

---

## Quality Check 1 — Off-Brand Rate

**What it measures:** Percentage of shortlisted trends with a `brand_fit` score below 6. Detects whether the LLM is shortlisting trends that don't genuinely fit Dior's aesthetic and clientele.

**Formula:**
```
off_brand_count = number of shortlisted trends where scores.brand_fit < 6
off_brand_rate = off_brand_count / total_shortlisted × 100
```

**Target:** 0%

| Metric | Value |
|--------|-------|
| Shortlisted trends | 5 |
| Trends with brand_fit < 6 | 0 |
| Brand_fit scores | t20: 10, t04: 10, t18: 10, t19: 10, t01: 9 |
| Off-brand rate | 0% |
| **Result** | **PASS** |

**Notes:** All 5 shortlisted trends achieved brand_fit ≥ 9. The LLM correctly identified the two most egregious off-brand trends — t13 (Relaxed Blazer Styling, brand_fit=3) and t28 (Woven Leather/Bottega Effect, brand_fit=3) — as disqualifying failures. t13 was penalized for its casual/lazy aesthetic conflicting with Dior's structured elegance. t28 was penalized for being competitor-brand content. The pre-filter correctly removed all 6 taboo-keyword-matched trends (streetwear ×2, logomania ×2, athleisure ×1, dupes ×1) before they reached the LLM.

---

## Quality Check 2 — Noise Reduction Rate

**What it measures:** Percentage of input trends correctly filtered out (pre-filter + LLM rejection combined). Detects whether the module is providing genuine signal compression.

**Formula:**
```
noise_reduction_rate = (total_input - shortlist_count) / total_input × 100
```

**Target:** ≥ 80%

| Metric | Value |
|--------|-------|
| Total input | 30 |
| Final shortlist count | 5 |
| Filtered out total | 25 |
| — Pre-filter removed | 15 |
| — LLM disqualified (below threshold or ranked out) | 10 |
| Noise reduction rate | **83.3%** |
| **Result** | **PASS** |

**Breakdown of what was filtered:**

| Filter Stage | Count | Examples |
|---|---|---|
| Taboo keyword (pre-filter) | 6 | streetwear, logomania, athleisure, dupes |
| Stale content >21 days (pre-filter) | 6 | t09, t10, t11, t24, t25 |
| Weak signal post_count < 5 (pre-filter) | 4 | t12, t14, t26, t29 (also caught t25 by staleness) |
| LLM brand_fit < 4 | 2 | t13 (brand_fit=3), t28 (brand_fit=3) |
| LLM composite < 6.5 | 2 | t15 (6.2), t27 (6.4), t30 (6.3) |
| Ranked out (qualified but below top 5) | 6 | t02, t03, t05, t16, t17 — all scored ≥7.4 |

**Notes:** 15 trends were removed at pre-filter before any LLM call, keeping LLM costs low. Of the 15 passed to the LLM, 10 did not make the final shortlist — 4 were disqualified by dimension thresholds, and 6 qualified but were ranked out by the top-5 limit. The strong Dior-aligned trends t02, t03, t05, t16, and t17 would be valid for a larger shortlist (e.g. top-8 for a full-week briefing).

---

## Quality Check 3 — Explanation Specificity Rate

**What it measures:** Percentage of shortlisted trends where reasoning contains a direct reference to a specific snippet, metric, keyword, or date from the original trend object.

**Target:** 100%

| Metric | Value |
|--------|-------|
| Shortlisted trends | 5 |
| Trends with specific evidence citation | 5 |
| Explanation specificity rate | **100%** |
| **Result** | **PASS** |

**Evidence citations per shortlisted trend:**

| Trend | Specific Citations in Reasoning |
|---|---|
| t20 Lady Dior Heritage | Snippet: "Lady Dior三十年——从戴安娜王妃到现在" · total_engagement: 158,000 · total_saves: 26,200 |
| t04 New Bar Jacket | Snippet: "Bar夹克是Dior最经典的轮廓" · total_engagement: 138,000 · Creator: "fashion_editor_paris" |
| t18 Top Handle Bag | Snippet: "Lady Dior永远是第一选择" · total_engagement: 142,000 · "文化活动、晚宴、开幕式" |
| t19 Cannage Quilting | Snippet: "Cannage图案的灵感来源——Dior先生椅子上的藤编" · total_engagement: 118,000 · post date: 2026-03-23 |
| t01 Soft Tailoring | Snippet: "软裁剪西装让整体造型更显高级感，Dior这季做得最好" · total_engagement: 87,500 |

**Notes:** All 5 explanations cited at minimum one Chinese-language snippet and one specific metric. Zero generic statements like "this trend aligns with Dior values" without backing evidence. The Cannage entry is particularly strong — citing the historical origin story (Monsieur Dior's cane chair) makes the reasoning immediately usable as CA briefing language.

---

## Top Failure Examples

| # | Trend ID | Label | Issue | Expected | Actual |
|---|----------|-------|-------|----------|--------|
| 1 | t13 | Relaxed Blazer Styling | LLM correctly rejected (brand_fit=3) for casual aesthetic — but terminal log incorrectly labels it as a "threshold failure" rather than explicit brand rejection | Terminal output should distinguish LLM disqualification from rank cutoff | Both present in run_log but undifferentiated in terminal print |
| 2 | t02 | Feminine Floral Print Dressing | Strongly Dior-aligned (brand_fit=10, composite=8.6) but ranked out of top 5 | Would be valid for a top-8 shortlist | Correct behavior given 5-trend cap, but the CA could miss a strong signal |
| 3 | t28 | Woven Leather and Bottega Effect | LLM correctly gave brand_fit=3 (competitor content) — but this should have been pre-filtered earlier since all evidence.posts are Bottega Veneta brand, not Dior | Should be caught at pre-filter by checking if all post brands are non-Dior | Pre-filter currently only checks label/summary for taboos, not brand field in posts |
| 4 | t27 | Lady Dior New Colorways | Correctly scored low (composite=6.4) due to redundancy with t20 — but redundancy detection relies entirely on LLM judgment with no explicit deduplication | Explicit deduplication step before LLM call would be more reliable | LLM correctly handled this but only because both trends were in the same batch |
| 5 | t15 | Feminine Layered Knitwear | Composite 6.2 — just below 6.5 threshold. LLM noted overlap with t05 (Silk Layering) | If batch ordering had separated t05 and t15, LLM might have scored t15 differently | Result is correct but sensitive to batch ordering |

---

## Fix Planned for Next Week

**Add brand field check to pre-filter (scorer.py):** If 100% of posts in `evidence.posts` reference a brand that is not in `brand_profile.brand_name` or preferred brands, flag the trend with a `non_dior_brand_saturation` warning and add it as a secondary rejection reason. This would have caught t28 (Bottega Veneta) at pre-filter without needing LLM judgment. Implementation: count distinct brands in `evidence.posts`, reject if Dior appears in 0 of N posts and total posts ≥ 3.

**Improve terminal logging terminology:** Separate "LLM disqualified" (failed dimension threshold) from "ranked out" (qualified but outside top-5 cap) in the Step 3 terminal output. Currently both are labeled as "LLM-rejected" which is misleading. The run_log.json already captures this correctly.

---

## Actual Run Results Summary

```
Total input trends:        30
Pre-filter rejected:       15
Passed to LLM:             15
LLM evaluated:             15
LLM rejected:              10
Final shortlist:           5
Noise reduction rate:      83.3%
```

### All LLM Evaluation Scores

| Trend ID | Label | freshness | brand_fit | category_fit | materiality | actionability | composite | shortlist |
|----------|-------|-----------|-----------|--------------|-------------|---------------|-----------|-----------|
| t01 | Soft Tailoring Revival | 9 | 9 | 8 | 8 | 9 | 8.60 | ✅ (rank 5) |
| t02 | Feminine Floral Print Dressing | 8 | 10 | 8 | 9 | 9 | 8.60 | ranked out |
| t03 | Couture Detail Incorporation | 7 | 10 | 8 | 9 | 9 | 8.60 | ranked out |
| t04 | New Bar Jacket Reinterpretation | 7 | 10 | 8 | 9 | 10 | 8.80 | ✅ (rank 2) |
| t05 | Silk Layering and Transparency | 8 | 8 | 7 | 7 | 7 | 7.40 | ranked out |
| t13 | Relaxed Blazer Styling | 6 | 3 | 5 | 5 | 5 | 4.50 | ❌ brand_fit < 4 |
| t15 | Feminine Layered Knitwear | 7 | 6 | 6 | 6 | 5 | 6.20 | ❌ composite < 6.5 |
| t16 | Saddle Bag Styling Revival | 8 | 9 | 8 | 9 | 9 | 8.60 | ranked out |
| t17 | Structured Tote Resurgence | 7 | 8 | 8 | 8 | 8 | 7.80 | ranked out |
| t18 | Top Handle Bag Elegance | 7 | 10 | 9 | 9 | 9 | 8.80 | ✅ (rank 3) |
| t19 | Cannage Quilting Detail Focus | 8 | 10 | 9 | 8 | 9 | 8.80 | ✅ (rank 4) |
| t20 | Lady Dior Styling and Heritage | 8 | 10 | 9 | 9 | 9 | 9.00 | ✅ (rank 1) |
| t27 | Lady Dior New Colorways | 7 | 8 | 7 | 8 | 5 | 6.40 | ❌ composite < 6.5 |
| t28 | Woven Leather and Bottega Effect | 7 | 3 | 6 | 7 | 5 | 4.80 | ❌ brand_fit < 4 |
| t30 | Dior Saddle Bag Mini Variations | 7 | 8 | 7 | 7 | 5 | 6.30 | ❌ composite < 6.5 |
