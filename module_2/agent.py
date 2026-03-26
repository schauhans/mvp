"""
agent.py — Main entry point for Module 2: Trend Relevance & Materiality Filter Agent.

Run with: python agent.py

Reads:  data/trend_objects.json  (Module 1 output format)
        brand_profile.json

Writes: outputs/output_shortlist.json
        outputs/run_log.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from scorer import run_prefilter_batch
from evaluator import evaluate_batch, select_shortlist

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "trend_objects.json"
OUTPUT_SHORTLIST_FILE = BASE_DIR / "outputs" / "output_shortlist.json"
RUN_LOG_FILE = BASE_DIR / "outputs" / "run_log.json"

# ── Constants ──────────────────────────────────────────────────────────────────
AGENT_NAME = "Trend Relevance & Materiality Filter"
MODULE1_RUN_ID = "run_0001"
RUN_ID = "run_0001_m2"
MAX_SHORTLIST = 5


def resolve_brand_profile(brand_slug: str) -> Path:
    """
    Find the brand profile JSON for the given slug.
    Looks for brand_profile_{slug}.json first, falls back to brand_profile.json.
    """
    specific = BASE_DIR / f"brand_profile_{brand_slug}.json"
    if specific.exists():
        return specific
    default = BASE_DIR / "brand_profile.json"
    if not default.exists():
        raise FileNotFoundError(f"No brand profile found for '{brand_slug}' and no default brand_profile.json")
    return default


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Union[dict, list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {path}")


def build_shortlist_output(
    shortlisted: list,
    all_evaluations: list,
    prefilter_rejected: list,
    total_input: int,
    generated_at: str
) -> dict:
    """Build the output_shortlist.json structure."""
    shortlist_items = []
    for rank, ev in enumerate(shortlisted, start=1):
        scores = ev.get("scores", {})
        item = {
            "rank": rank,
            "trend_id": ev.get("trend_id"),
            "label": ev.get("label", ""),
            "category": ev.get("category", ""),
            "composite_score": ev.get("composite_score"),
            "scores": {
                "freshness": scores.get("freshness"),
                "brand_fit": scores.get("brand_fit"),
                "category_fit": scores.get("category_fit"),
                "materiality": scores.get("materiality"),
                "actionability": scores.get("actionability")
            },
            "confidence": ev.get("confidence"),
            "why_selected": ev.get("reasoning", ""),
            "evidence_references": ev.get("evidence_references", []),
            "metric_signal": {
                "total_engagement": ev.get("metric_signal", {}).get("total_engagement"),
                "post_count": ev.get("metric_signal", {}).get("post_count"),
                "avg_engagement": ev.get("metric_signal", {}).get("avg_engagement")
            },
            "disqualifying_reason": None
        }
        shortlist_items.append(item)

    return {
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "brand": brand_name,
        "module1_run_id": MODULE1_RUN_ID,
        "total_evaluated": total_input,
        "total_prefilter_rejected": len(prefilter_rejected),
        "total_shortlisted": len(shortlisted),
        "shortlist": shortlist_items
    }


def build_run_log(
    shortlisted: list,
    all_evaluations: list,
    prefilter_rejected: list,
    total_input: int,
    generated_at: str
) -> dict:
    """Build the run_log.json structure."""
    shortlist_ids = [ev.get("trend_id") for ev in shortlisted]
    return {
        "run_id": RUN_ID,
        "agent_name": AGENT_NAME,
        "module1_run_id": MODULE1_RUN_ID,
        "brand": brand_name,
        "generated_at": generated_at,
        "total_input": total_input,
        "prefilter_rejections": prefilter_rejected,
        "llm_evaluations": all_evaluations,
        "shortlist_ids": shortlist_ids,
        "output_file": "outputs/output_shortlist.json"
    }


def main():
    parser = argparse.ArgumentParser(description="Module 2: Trend Relevance & Materiality Filter")
    parser.add_argument(
        "--brand", default="dior",
        help="Brand slug (e.g. dior, chanel, louis_vuitton). Loads brand_profile_{slug}.json."
    )
    args = parser.parse_args()
    brand_slug = args.brand.lower().strip()

    brand_profile_path = resolve_brand_profile(brand_slug)
    brand_profile = load_json(brand_profile_path)
    brand_name = brand_profile.get("brand_name", brand_slug)

    print("=" * 60)
    print(f"Module 2: {AGENT_NAME}")
    print(f"Brand: {brand_name}  (profile: {brand_profile_path.name})")
    print(f"Run ID: {RUN_ID}")
    print("=" * 60)

    # ── Load inputs ────────────────────────────────────────────────────────────
    print(f"\nLoading trend objects from {DATA_FILE}...")
    raw_data = load_json(DATA_FILE)
    all_trends = raw_data.get("trend_objects", [])
    total_input = len(all_trends)
    print(f"Loaded {total_input} trend objects.")

    # ── Step 1: Deterministic pre-filter ──────────────────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 1 — Deterministic Pre-Filter")
    print(f"{'─'*60}")
    passed_trends, prefilter_rejected = run_prefilter_batch(all_trends, brand_profile)

    print(f"\nPre-filter results:")
    print(f"  Passed:   {len(passed_trends)}")
    print(f"  Rejected: {len(prefilter_rejected)}")
    if prefilter_rejected:
        print("\nRejected trends:")
        for r in prefilter_rejected:
            print(f"  [{r['trend_id']}] {r['label']}")
            print(f"       Reason: {r['reason']}")

    if not passed_trends:
        print("\n[WARNING] No trends passed the pre-filter. Nothing to evaluate.")
        sys.exit(0)

    # ── Step 2: LLM Evaluation ─────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"STEP 2 — LLM Evaluation ({len(passed_trends)} trends in batches of 5)")
    print(f"{'─'*60}")

    all_evaluations = evaluate_batch(passed_trends, brand_profile)

    # Enrich evaluations with label, category, and metric_signal from original trend objects
    trend_lookup = {t["trend_id"]: t for t in all_trends}
    for ev in all_evaluations:
        tid = ev.get("trend_id")
        if tid and tid in trend_lookup:
            original = trend_lookup[tid]
            ev["label"] = original.get("label", "")
            ev["category"] = original.get("category", "")
            metrics = original.get("metrics", {})
            ev["metric_signal"] = {
                "total_engagement": metrics.get("total_engagement"),
                "post_count": metrics.get("post_count"),
                "avg_engagement": metrics.get("avg_engagement")
            }

    print(f"\nLLM evaluation complete: {len(all_evaluations)} trends evaluated")

    # ── Step 3: Ranking and Selection ──────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"STEP 3 — Ranking & Shortlist Selection (top {MAX_SHORTLIST})")
    print(f"{'─'*60}")

    shortlisted = select_shortlist(all_evaluations, max_shortlist=MAX_SHORTLIST)

    print(f"\nShortlist ({len(shortlisted)} trends selected):")
    if shortlisted:
        for i, ev in enumerate(shortlisted, start=1):
            print(f"  #{i} [{ev.get('trend_id')}] {ev.get('label', '')} — score: {ev.get('composite_score', 0):.2f}")
    else:
        print("  No trends met the shortlist criteria.")

    # Non-shortlisted LLM-evaluated trends (for log)
    shortlist_ids = {ev.get("trend_id") for ev in shortlisted}
    llm_rejected = [
        ev for ev in all_evaluations
        if ev.get("trend_id") not in shortlist_ids
    ]
    if llm_rejected:
        print(f"\nLLM-rejected trends ({len(llm_rejected)}):")
        for ev in llm_rejected:
            reason = ev.get("disqualifying_reason") or "Did not meet composite_score or dimension thresholds"
            print(f"  [{ev.get('trend_id')}] {ev.get('label', '')} — {reason}")

    # ── Step 4: Write Outputs ──────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("STEP 4 — Writing Output Files")
    print(f"{'─'*60}")

    generated_at = datetime.now(timezone.utc).isoformat()

    shortlist_output = build_shortlist_output(
        shortlisted=shortlisted,
        all_evaluations=all_evaluations,
        prefilter_rejected=prefilter_rejected,
        total_input=total_input,
        generated_at=generated_at
    )
    save_json(OUTPUT_SHORTLIST_FILE, shortlist_output)

    run_log = build_run_log(
        shortlisted=shortlisted,
        all_evaluations=all_evaluations,
        prefilter_rejected=prefilter_rejected,
        total_input=total_input,
        generated_at=generated_at
    )
    save_json(RUN_LOG_FILE, run_log)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("RUN SUMMARY")
    print(f"{'='*60}")
    print(f"Total input trends:        {total_input}")
    print(f"Pre-filter rejected:       {len(prefilter_rejected)}")
    print(f"Passed to LLM:             {len(passed_trends)}")
    print(f"LLM evaluated:             {len(all_evaluations)}")
    print(f"LLM rejected:              {len(llm_rejected)}")
    print(f"Final shortlist:           {len(shortlisted)}")
    noise_reduction = (total_input - len(shortlisted)) / total_input * 100 if total_input > 0 else 0
    print(f"Noise reduction rate:      {noise_reduction:.1f}%")
    print(f"\nOutputs written to:")
    print(f"  {OUTPUT_SHORTLIST_FILE}")
    print(f"  {RUN_LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
