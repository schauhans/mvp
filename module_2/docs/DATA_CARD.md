# DATA_CARD.md — Module 2: Trend Relevance & Materiality Filter Agent

## Dataset Identity

| Field | Value |
|-------|-------|
| **Dataset name** | Synthetic XHS Trend Objects — Dior Spring 2026 |
| **Version** | v1.0 (synthetic baseline) |
| **Created** | 2026-03-25 |
| **Created for** | Module 2 development and evaluation |
| **Schema** | Module 1 XHS Trend Object Builder output schema |

---

## Data Source

**Source:** Synthetic trend objects modeled on Module 1 XHS (Xiaohongshu) Trend Object Builder schema.

These are **not real XHS posts**. All post IDs, creator handles, snippet text, engagement numbers, and dates are fabricated to closely simulate the statistical and structural properties of real Module 1 output.

**Why synthetic?** Module 1 (XHS Trend Object Builder) has not yet completed a real production batch run at the time Module 2 was built. This synthetic dataset enables Module 2 development, testing, and evaluation to proceed independently.

---

## Brand and Category Scope

| Field | Value |
|-------|-------|
| **Brand** | Christian Dior |
| **Categories** | ready-to-wear, leather goods |
| **Beauty category** | Excluded — not in scope for this brand run |
| **Geography** | China (Xiaohongshu signals) |
| **Language** | Chinese (Simplified), with some English keywords |

---

## Dataset Volume and Composition

| Field | Value |
|-------|-------|
| **Total trend objects** | 30 |
| **Ready-to-wear trends** | 15 |
| **Leather goods trends** | 15 |

### Ready-to-Wear Breakdown

| Type | Count | Trend IDs |
|------|-------|-----------|
| Strong on-brand (Dior-aligned) | 5 | t01–t05 |
| Off-brand (should be rejected) | 3 | t06, t07, t08 |
| Stale (last post >21 days ago) | 3 | t09, t10, t11 |
| Weak signal (low post/engagement) | 2 | t12, t14 |
| Duplicate/overlapping | 2 | t13 (overlaps t01), t15 (overlaps t05) |

### Leather Goods Breakdown

| Type | Count | Trend IDs |
|------|-------|-----------|
| Strong on-brand (Dior-aligned) | 5 | t16–t20 |
| Off-brand (should be rejected) | 3 | t21, t22, t23 |
| Stale (last post >21 days ago) | 3 | t24, t25, t25 |
| Weak signal (low post/engagement) | 2 | t26, t29 |
| Duplicate/overlapping | 2 | t27 (overlaps t20), t30 (overlaps t16) |

---

## Date Range

| Field | Value |
|-------|-------|
| **Earliest post date in dataset** | 2026-01-25 |
| **Latest post date in dataset** | 2026-03-24 |
| **Run/evaluation date** | 2026-03-25 |
| **Staleness cutoff** | 2026-03-04 (21 days before run date) |

---

## Engagement Metric Ranges (Synthetic)

| Trend Type | total_engagement range | post_count range |
|------------|------------------------|------------------|
| Strong on-brand | 82,000 – 158,000 | 9 – 13 |
| Medium signal | 43,000 – 74,000 | 6 – 9 |
| Off-brand (high engagement, wrong brand) | 48,000 – 122,000 | 6 – 8 |
| Stale | 48,000 – 62,000 | 7 – 8 |
| Weak signal | 1,840 – 2,800 | 3 – 4 |

---

## Real Data Status

**All 30 trend objects are synthetic.** No real Xiaohongshu user data, post data, or creator data is used.

**Module 1 real XHS batch run is targeted for Week 11.** Once completed, Module 2 can be re-run against the real batch using `python agent.py` with no code changes — only the input file needs to be replaced.

---

## Known Constraints and Limitations

1. **No cross-platform identity matching** — Creator handles are fictional strings. In production, creator identity resolution across platforms is out of scope for this module. Real creator IDs would be SHA-256 hashed in the evidence layer.

2. **Commenter IDs would be hashed in real data** — Any user-level identifiers (commenters, likers) would be SHA-256 hashed before processing in production to comply with privacy requirements.

3. **Engagement distributions are manually calibrated** — Real XHS engagement has a heavy-tailed distribution. Synthetic engagement values are designed to test Module 2 logic (e.g., above/below threshold), not to reproduce exact real-world distributions.

4. **Beauty category excluded** — This brand profile run focuses on ready-to-wear and leather goods only. Beauty is a separate module configuration.

5. **Snippets are simplified Chinese** — Real XHS content is significantly more varied in register, slang, and emoji usage. Synthetic snippets are cleaner and more formal to aid testing.

6. **Duplicate trends are intentional** — t13/t01, t15/t05, t27/t20, and t30/t16 are designed to test whether the LLM evaluation catches near-duplicate signal clusters. The pre-filter does not deduplicate — this is left to LLM judgment.

---

## Data Integrity Checks

Before running the agent, verify:
- All 30 trend objects have unique `trend_id` values
- All `evidence.posts[].date` values are ISO 8601 format
- All `metrics.total_engagement` values are positive integers
- All `evidence.snippets` arrays contain strings in Chinese

Run basic check:
```bash
python -c "
import json
data = json.load(open('data/trend_objects.json'))
trends = data['trend_objects']
ids = [t['trend_id'] for t in trends]
print(f'Trend count: {len(trends)}')
print(f'Unique IDs: {len(set(ids))}')
print('All IDs unique:', len(ids) == len(set(ids)))
"
```
