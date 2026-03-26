"""
evaluator.py — LLM evaluation engine for Module 2 Trend Relevance & Materiality Filter Agent.

Sends batches of pre-filtered trend objects to Claude and returns structured scores.
Processes 5 trends per API call to manage rate limits.
"""

import json
import os
import time
from typing import Optional

import anthropic

from prompts import build_system_prompt, build_batch_evaluation_prompt

# Use DEFAULT_MODEL env var so the whole pipeline shares one model setting.
MODEL = os.environ.get("DEFAULT_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 4096  # batch of 5 needs more headroom than single trend
BATCH_SIZE = 5
TODAY = "2026-03-25"


def _get_client() -> anthropic.Anthropic:
    """Initialize Anthropic client from ANTHROPIC_API_KEY."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Add it to your .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


def _call_llm(client: anthropic.Anthropic, prompt: str, system_prompt: str, attempt: int = 1) -> Optional[str]:
    """
    Call the LLM via OpenRouter and return the raw text response.
    Retries once on failure.
    """
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.RateLimitError as e:
        if attempt == 1:
            print(f"  [Rate limit hit] Waiting 10s before retry...")
            time.sleep(10)
            return _call_llm(client, prompt, system_prompt, attempt=2)
        print(f"  [ERROR] Rate limit on retry: {e}")
        return None
    except anthropic.APIError as e:
        if attempt == 1:
            print(f"  [API error] {e} — retrying once...")
            time.sleep(3)
            return _call_llm(client, prompt, system_prompt, attempt=2)
        print(f"  [ERROR] API error on retry: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Unexpected error calling LLM: {e}")
        return None


def _parse_llm_response(raw: str, expected_trend_ids: list) -> list:
    """
    Parse the LLM response into a list of evaluation dicts.
    Handles both array responses (batch) and single-object responses.
    Returns a list of evaluation dicts. Missing evaluations are logged.
    """
    if not raw:
        return []

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed: {e}")
        print(f"  [DEBUG] Raw response (first 500 chars): {raw[:500]}")
        return []

    # Normalize to list
    if isinstance(parsed, dict):
        parsed = [parsed]
    elif not isinstance(parsed, list):
        print(f"  [ERROR] Unexpected LLM response type: {type(parsed)}")
        return []

    # Validate each evaluation has required fields
    valid = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        trend_id = item.get("trend_id")
        if not trend_id:
            print(f"  [WARN] Evaluation missing trend_id, skipping: {str(item)[:200]}")
            continue
        # Ensure composite_score is present and numeric
        if "composite_score" not in item:
            scores = item.get("scores", {})
            if scores:
                cs = (
                    scores.get("freshness", 0) * 0.20 +
                    scores.get("brand_fit", 0) * 0.30 +
                    scores.get("category_fit", 0) * 0.20 +
                    scores.get("materiality", 0) * 0.15 +
                    scores.get("actionability", 0) * 0.15
                )
                item["composite_score"] = round(cs, 2)
        valid.append(item)

    return valid


def evaluate_batch(
    trends: list,
    brand_profile: dict,
    client: Optional[anthropic.Anthropic] = None
) -> list:
    """
    Evaluate a list of trend objects using the LLM.
    Processes in batches of BATCH_SIZE.

    Returns list of evaluation dicts (one per trend that was successfully evaluated).
    """
    if client is None:
        client = _get_client()

    system_prompt = build_system_prompt(brand_profile)
    all_evaluations = []
    total = len(trends)

    # Split into batches
    batches = [trends[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    evaluated_count = 0
    for batch_num, batch in enumerate(batches, start=1):
        batch_start = evaluated_count + 1
        batch_end = evaluated_count + len(batch)
        print(f"\nEvaluating trends {batch_start}-{batch_end} of {total} (batch {batch_num}/{len(batches)})...")

        prompt = build_batch_evaluation_prompt(brand_profile, batch, today=TODAY)
        raw_response = _call_llm(client, prompt, system_prompt)

        if raw_response is None:
            print(f"  [ERROR] Batch {batch_num} failed — all {len(batch)} trends in this batch will be skipped")
            evaluated_count += len(batch)
            continue

        batch_ids = [t.get("trend_id") for t in batch]
        evaluations = _parse_llm_response(raw_response, batch_ids)

        if not evaluations:
            print(f"  [ERROR] Could not parse any evaluations from batch {batch_num}")
        else:
            print(f"  Successfully parsed {len(evaluations)} evaluation(s) from batch {batch_num}")
            all_evaluations.extend(evaluations)

        evaluated_count += len(batch)

        # Brief pause between batches to avoid rate limits
        if batch_num < len(batches):
            time.sleep(1)

    return all_evaluations


def select_shortlist(evaluations: list, max_shortlist: int = 5) -> list:
    """
    From a list of LLM evaluations, select trends that pass qualification criteria
    and return the top N by composite_score.

    Qualification criteria:
    - shortlist == True (LLM's judgment)
    - composite_score >= 6.5
    - No individual dimension score below 4
    """
    qualified = []

    for ev in evaluations:
        # LLM must have shortlisted it
        if not ev.get("shortlist", False):
            continue

        # Composite score threshold
        composite = ev.get("composite_score", 0)
        if composite < 6.5:
            ev["shortlist"] = False
            ev["disqualifying_reason"] = (
                ev.get("disqualifying_reason") or
                f"composite_score {composite:.2f} below 6.5 threshold"
            )
            continue

        # No dimension below 4
        scores = ev.get("scores", {})
        failed_dim = None
        for dim, score in scores.items():
            if score < 4:
                failed_dim = dim
                break
        if failed_dim:
            ev["shortlist"] = False
            ev["disqualifying_reason"] = (
                ev.get("disqualifying_reason") or
                f"Dimension '{failed_dim}' scored {scores[failed_dim]:.1f} — below minimum of 4"
            )
            continue

        qualified.append(ev)

    # Sort by composite_score descending
    qualified.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    return qualified[:max_shortlist]
