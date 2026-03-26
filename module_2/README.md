# Module 2: Trend Relevance & Materiality Filter Agent

## What This Module Does

Module 2 is the **Trend Relevance & Materiality Filter Agent** for the luxury retail AI system. It takes structured Trend Objects produced by Module 1 (XHS Trend Object Builder) and applies a two-stage qualification pipeline to produce a shortlist of the most material, brand-relevant, and actionable trends for a given brand and product category. The goal is not to find more trends — it is to eliminate the burden on Client Advisors (CAs) of deciding which trends are worth acting on.

The agent applies deterministic pre-filtering (freshness, engagement thresholds, brand taboo detection) before calling Claude to evaluate brand fit, category fit, materiality, and actionability. Only trends that pass all criteria are shortlisted — with a maximum of 5 per run. The output is designed to be consumed directly by downstream reporting and clienteling modules, with structured JSON including scores, rankings, and evidence-grounded reasoning for each shortlisted trend.

## Prerequisites

- Python 3.9 or higher
- `anthropic` Python package
- `ANTHROPIC_API_KEY` environment variable set

## Installation

```bash
pip install anthropic
```

## Setup

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## How to Run

```bash
cd module2-trend-filter
python agent.py
```

The agent will:
1. Load `data/trend_objects.json` (30 synthetic trend objects)
2. Load `brand_profile.json` (Christian Dior profile)
3. Run deterministic pre-filter (scorer.py) — rejects trends without LLM call
4. Send passing trends to Claude in batches of 5 (evaluator.py)
5. Score, rank, and select the top 5 shortlisted trends
6. Write output files

## Output Files

| File | Description |
|------|-------------|
| `outputs/output_shortlist.json` | Final shortlist with ranks, scores, reasoning, and evidence references |
| `outputs/run_log.json` | Full audit trail: all LLM evaluations, all pre-filter rejections, all decisions |

## File Structure

```
module2-trend-filter/
├── agent.py              # Main entry point — run this
├── evaluator.py          # LLM evaluation engine (batches of 5, Claude API)
├── scorer.py             # Deterministic pre-filter (no LLM)
├── prompts.py            # System prompt and evaluation prompt templates
├── brand_profile.json    # Christian Dior brand configuration
├── feedback.csv          # CA reviewer feedback template
├── data/
│   └── trend_objects.json    # 30 synthetic trend objects (Module 1 format)
├── outputs/
│   ├── output_shortlist.json # Final shortlist output
│   └── run_log.json          # Full run audit log
├── docs/
│   ├── IO_CONTRACT.md    # Input/output schema for upstream and downstream modules
│   ├── DATA_CARD.md      # Dataset provenance and constraints
│   └── EVAL_REPORT.md    # Quality evaluation report
└── README.md
```

## How Downstream Modules Consume the Output

Downstream modules (Module 3 — Reporting, Module 4 — Clienteling) should read `outputs/output_shortlist.json`.

Key fields for downstream consumption:

```json
{
  "shortlist": [
    {
      "rank": 1,
      "trend_id": "t04",
      "label": "New Bar Jacket Reinterpretation",
      "category": "ready-to-wear",
      "composite_score": 8.75,
      "scores": {
        "freshness": 9,
        "brand_fit": 10,
        "category_fit": 9,
        "materiality": 8,
        "actionability": 9
      },
      "confidence": "high",
      "why_selected": "Evidence-grounded 3-5 sentence reasoning...",
      "evidence_references": ["Bar夹克是Dior最经典的轮廓...", "total_engagement: 138,000"],
      "metric_signal": {
        "total_engagement": 138000,
        "post_count": 12,
        "avg_engagement": 11500
      }
    }
  ]
}
```

The `why_selected` and `evidence_references` fields provide ready-to-use CA briefing language. The `metric_signal` provides the quantitative evidence. The `rank` field provides the priority order for briefing focus.

## Documentation

- `docs/IO_CONTRACT.md` — Full input/output schema, field definitions, and assumptions
- `docs/DATA_CARD.md` — Dataset provenance, known constraints, and real-data timeline
- `docs/EVAL_REPORT.md` — Quality evaluation report (complete after each run)
