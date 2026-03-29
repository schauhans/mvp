#!/usr/bin/env python3
"""
evaluator.py — Module 3 Evaluation Harness
===========================================
Loads every trend card from module_3/data/batch_outputs/ and scores each
against 3 quality checks. Saves full results to module_3/eval/eval_results.json.

Checks:
  1. Metric contextualization rate (automated)
  2. Conversation starter quality (LLM-judged, 1–5)
  3. Persona match specificity (LLM-judged, 1–5)
"""

import json
import os
import re
import sys
import time
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────
def _load_env():
    root = Path(__file__).parent.parent.parent
    for p in [root / ".env", Path(__file__).parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break

_load_env()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
_raw_model = os.environ.get("DEFAULT_MODEL", "openai/gpt-4o-mini")
# OpenRouter requires "provider/model" format. If the env var is a bare Anthropic
# model ID (no slash), fall back to a known-good OpenRouter model.
MODEL = _raw_model if "/" in _raw_model else "openai/gpt-4o-mini"

BATCH_DIR  = Path(__file__).parent.parent / "data" / "batch_outputs"
EVAL_DIR   = Path(__file__).parent
RESULTS_PATH = EVAL_DIR / "eval_results.json"


# ── OpenRouter client ─────────────────────────────────────────────
def get_client():
    from openai import OpenAI
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


# ── Parsing ───────────────────────────────────────────────────────
def parse_cards_from_file(filepath: Path) -> list:
    """Parse one markdown card file into a list of card dicts."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # File-level header: "# CA Trend Brief — Dior Shanghai"
    header_m = re.search(r"# CA Trend Brief — (.+)", content)
    header   = header_m.group(1).strip() if header_m else filepath.stem
    parts    = header.rsplit(" ", 1)
    brand    = parts[0].strip() if len(parts) > 1 else header
    city     = parts[1].strip() if len(parts) > 1 else "Unknown"

    # Split into individual cards by "## tXX: ..." marker
    sections = re.split(r"\n## ([tT]\d+): [^\n]+\n", content)
    # sections[0] = file header text
    # sections[1,3,5,...] = trend_ids  ("t18", "t20", ...)
    # sections[2,4,6,...] = card body text

    cards = []
    for i in range(1, len(sections), 2):
        trend_id  = sections[i].strip()
        card_text = sections[i + 1] if i + 1 < len(sections) else ""

        # Trend label from the ### heading
        label_m     = re.search(r"^### (.+)", card_text, re.MULTILINE)
        trend_label = label_m.group(1).strip() if label_m else trend_id

        # Category
        cat_m    = re.search(r"\*\*Category:\*\*\s*([^|]+)", card_text)
        category = cat_m.group(1).strip() if cat_m else ""

        # DATA SIGNAL block (between **DATA SIGNAL** and **CONFIDENCE NOTE**)
        ds_m        = re.search(r"\*\*DATA SIGNAL\*\*(.*?)\*\*CONFIDENCE NOTE\*\*", card_text, re.DOTALL)
        data_signal = ds_m.group(1).strip() if ds_m else ""

        # TREND OVERVIEW block
        ov_m          = re.search(r"\*\*TREND OVERVIEW\*\*(.*?)---", card_text, re.DOTALL)
        trend_overview = ov_m.group(1).strip() if ov_m else ""

        # Chinese conversation starter
        # Handles both "Chinese:" and "Chinese (use this first, in-store and on WeChat):"
        zh_m           = re.search(r"Chinese[^:\n]*:\s*\n「(.+?)」", card_text, re.DOTALL)
        chinese_starter = zh_m.group(1).strip() if zh_m else ""

        # Match rationale ("Why this trend fits:")
        rat_m          = re.search(
            r"\*\*Why this trend fits:\*\*\s*(.+?)(?=\*\*Match score|\*\*This trend)",
            card_text, re.DOTALL
        )
        match_rationale = rat_m.group(1).strip() if rat_m else ""

        cards.append({
            "file":           filepath.name,
            "brand":          brand,
            "city":           city,
            "trend_id":       trend_id,
            "trend_label":    trend_label,
            "category":       category,
            "data_signal":    data_signal,
            "trend_overview": trend_overview,
            "chinese_starter": chinese_starter,
            "match_rationale": match_rationale,
        })

    return cards


# ── Check 1: Metric Contextualization (automated) ─────────────────
def check_metric_contextualization(card: dict) -> dict:
    """
    PASS if every numeric metric line in DATA SIGNAL has:
      (a) a benchmark comparison, (b) a sample size, (c) a date.
    FAIL otherwise. Skips qualitative-only lines (Brand relevance).
    """
    data_signal = card.get("data_signal", "")
    if not data_signal:
        return {"result": "FAIL", "score": 0,
                "reason": "missing field: no DATA SIGNAL section found"}

    # All bullet lines that contain a numeric value (% or 3+ digit number)
    all_lines     = re.findall(r"^-\s*.+$", data_signal, re.MULTILINE)
    numeric_lines = [l for l in all_lines if re.search(r"\d+\.?\d*%|\b\d{3,}\b", l)]

    if not numeric_lines:
        return {"result": "FAIL", "score": 0,
                "reason": "no numeric metric lines found in DATA SIGNAL"}

    failures = []
    for line in numeric_lines:
        ll = line.lower()
        # Skip qualitative lines
        if re.match(r"-\s*brand relevance:", ll):
            continue

        has_benchmark = bool(re.search(r"\bavg\b|benchmark|vs\.", ll))
        has_sample    = bool(re.search(r"\d+\s*posts?", ll))
        has_date      = bool(re.search(
            r"\bjan|\bfeb|\bmar|\bapr|\bmay|\bjun|"
            r"\bjul|\baug|\bsep|\boct|\bnov|\bdec|\b20\d\d\b",
            ll
        ))

        missing = []
        if not has_benchmark:
            missing.append("benchmark")
        if not has_sample:
            missing.append("sample size")
        if not has_date:
            missing.append("date")

        if missing:
            failures.append(f"'{line.strip()[:70]}' — missing: {', '.join(missing)}")

    if failures:
        return {"result": "FAIL", "score": 0, "reason": " | ".join(failures)}

    return {"result": "PASS", "score": 1,
            "reason": "all numeric metrics have benchmark, sample size, and date"}


# ── Check 2: Conversation starter quality (LLM-judged) ────────────
STARTER_PROMPT = (
    "Score this luxury retail WeChat conversation starter from 1–5 on whether it sounds "
    "natural and intimate (like a trusted friend) vs corporate and templated (like a sales script). "
    "5 = could send immediately, 1 = obvious template, nobody would send this verbatim. "
    "Return only a JSON object with keys: score (int), reason (one sentence).\n\n"
    "Conversation starter:\n{starter}"
)


def check_conversation_starter(client, card: dict) -> dict:
    starter = card.get("chinese_starter", "")
    if not starter:
        return {"score": None,
                "reason": "missing field: no Chinese conversation starter found"}

    prompt = STARTER_PROMPT.format(starter=starter)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw).rstrip("`").strip()
        return json.loads(raw)
    except Exception as e:
        return {"score": None, "reason": f"LLM call failed: {e}"}


# ── Check 3: Persona match specificity (LLM-judged) ───────────────
PERSONA_PROMPT = (
    "Score this persona match rationale from 1–5 on whether it specifically references "
    "the trend's evidence and category (5 = directly cites trend details) or is generic "
    "and could apply to any trend (1 = vague, no specific evidence cited). "
    "Return only a JSON object with keys: score (int), reason (one sentence).\n\n"
    "Trend label: {label}\n"
    "Category: {category}\n"
    "Trend overview: {overview}\n"
    "Match rationale: {rationale}"
)


def check_persona_specificity(client, card: dict) -> dict:
    rationale = card.get("match_rationale", "")
    if not rationale:
        return {"score": None,
                "reason": "missing field: no match_rationale found"}

    prompt = PERSONA_PROMPT.format(
        label    = card.get("trend_label", ""),
        category = card.get("category", ""),
        overview = card.get("trend_overview", "")[:300],
        rationale = rationale,
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw).rstrip("`").strip()
        return json.loads(raw)
    except Exception as e:
        return {"score": None, "reason": f"LLM call failed: {e}"}


# ── Main ──────────────────────────────────────────────────────────
def main():
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set. Add it to .env")
        sys.exit(1)

    if not BATCH_DIR.exists():
        print(f"ERROR: {BATCH_DIR} not found.")
        sys.exit(1)

    md_files = sorted(BATCH_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md card files found in {BATCH_DIR}")
        sys.exit(1)

    print(f"Batch directory : {BATCH_DIR}")
    print(f"Card files found: {len(md_files)}")
    print(f"Model           : {MODEL}\n")

    # Parse
    all_cards = []
    for f in md_files:
        cards = parse_cards_from_file(f)
        print(f"  {f.name}: {len(cards)} card(s)")
        all_cards.extend(cards)

    print(f"\nTotal cards to evaluate: {len(all_cards)}\n{'='*60}\n")

    client = get_client()
    results = []

    for i, card in enumerate(all_cards, 1):
        label = f"{card['brand']} {card['city']} / {card['trend_label']}"
        print(f"[{i}/{len(all_cards)}] {label}")

        # Check 1 — automated
        c1 = check_metric_contextualization(card)
        print(f"  Check 1 (metric context)      : {c1['result']} — {c1['reason'][:90]}")

        # Check 2 — LLM
        c2 = check_conversation_starter(client, card)
        print(f"  Check 2 (starter quality)     : {c2.get('score')}/5 — {c2.get('reason','')[:90]}")
        time.sleep(0.4)

        # Check 3 — LLM
        c3 = check_persona_specificity(client, card)
        print(f"  Check 3 (persona specificity) : {c3.get('score')}/5 — {c3.get('reason','')[:90]}")
        time.sleep(0.4)

        print()
        results.append({
            "brand":       card["brand"],
            "city":        card["city"],
            "trend_id":    card["trend_id"],
            "trend_label": card["trend_label"],
            "category":    card["category"],
            "file":        card["file"],
            "check_1_metric_context":     c1,
            "check_2_starter_quality":    c2,
            "check_3_persona_specificity": c3,
        })

    # ── Summary stats ──────────────────────────────────────────────
    n = len(results)
    c1_pass   = sum(1 for r in results if r["check_1_metric_context"]["result"] == "PASS")
    c2_scores = [r["check_2_starter_quality"]["score"]     for r in results if r["check_2_starter_quality"]["score"]     is not None]
    c3_scores = [r["check_3_persona_specificity"]["score"] for r in results if r["check_3_persona_specificity"]["score"] is not None]

    summary = {
        "total_cards":            n,
        "check_1_pass_count":     c1_pass,
        "check_1_pass_rate_pct":  round(c1_pass / n * 100, 1) if n else 0,
        "check_2_avg_score":      round(sum(c2_scores) / len(c2_scores), 2) if c2_scores else None,
        "check_2_scored_cards":   len(c2_scores),
        "check_3_avg_score":      round(sum(c3_scores) / len(c3_scores), 2) if c3_scores else None,
        "check_3_scored_cards":   len(c3_scores),
    }

    output = {"summary": summary, "cards": results}

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"Results saved → {RESULTS_PATH}")
    print(f"Check 1 pass rate : {summary['check_1_pass_rate_pct']}%  ({c1_pass}/{n} cards)")
    print(f"Check 2 avg score : {summary['check_2_avg_score']}/5  ({len(c2_scores)} cards scored)")
    print(f"Check 3 avg score : {summary['check_3_avg_score']}/5  ({len(c3_scores)} cards scored)")


if __name__ == "__main__":
    main()
