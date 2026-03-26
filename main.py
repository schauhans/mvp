import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL


# ── Brand → XHS search keywords ────────────────────────────────────────────────
# Two buckets per brand: ready-to-wear and leather goods.
# The scraper tags every post it collects with whichever category bucket it ran for,
# so module 2's category pre-filter will accept them.
BRAND_KEYWORDS = {
    "dior": {
        "ready-to-wear": ["Dior新款成衣", "迪奥春夏穿搭", "Dior Bar夹克", "高定成衣穿搭"],
        "leather goods": ["Lady Dior", "迪奥手袋", "Dior Saddle包", "Dior包包新款"],
    },
    "chanel": {
        "ready-to-wear": ["Chanel春夏成衣", "香奈儿穿搭", "Chanel斜纹软呢", "Chanel新款"],
        "leather goods": ["Chanel包包", "香奈儿CF", "Classic Flap", "香奈儿手袋"],
    },
    "louis_vuitton": {
        "ready-to-wear": ["LV成衣新款", "Louis Vuitton穿搭", "LV春夏时装", "路易威登成衣"],
        "leather goods": ["LV包包", "LV Capucines", "LV Speedy", "路易威登手袋"],
    },
    "bottega_veneta": {
        "ready-to-wear": ["BV成衣", "Bottega Veneta穿搭", "安静奢华穿搭", "BV新款"],
        "leather goods": ["BV包包", "BV Jodie", "BV Andiamo", "编织皮具"],
    },
    "loewe": {
        "ready-to-wear": ["Loewe新款", "罗意威穿搭", "Loewe成衣", "Loewe春夏"],
        "leather goods": ["Loewe包包", "罗意威手袋", "Loewe Puzzle", "Loewe皮具"],
    },
    "amiri": {
        "ready-to-wear": ["Amiri穿搭", "Amiri新款", "Amiri牛仔", "Amiri时装"],
        "leather goods": ["Amiri包包", "Amiri皮衣", "Amiri皮具", "Amiri手袋"],
    },
    "celine": {
        "ready-to-wear": ["Celine成衣", "Celine穿搭", "极简奢侈穿搭", "Celine新款"],
        "leather goods": ["Celine包包", "Celine 16 bag", "Celine Triomphe", "赛琳手袋"],
    },
    "hermes": {
        "ready-to-wear": ["Hermes成衣", "爱马仕穿搭", "Hermes新款", "爱马仕时装"],
        "leather goods": ["Birkin包", "Kelly包", "爱马仕手袋", "Hermes皮具"],
    },
    "gucci": {
        "ready-to-wear": ["Gucci成衣", "古驰穿搭", "Gucci新款", "Gucci时装"],
        "leather goods": ["Gucci包包", "Gucci Dionysus", "古驰手袋", "Gucci皮具"],
    },
}


def get_keywords(slug: str, brand: str) -> dict:
    """Return keyword lists for the brand, with a generic fallback."""
    if slug in BRAND_KEYWORDS:
        return BRAND_KEYWORDS[slug]
    return {
        "ready-to-wear": [f"{brand}新款", f"{brand}穿搭", "高定成衣", "奢侈品时装"],
        "leather goods":  [f"{brand}包包", f"{brand}手袋", "精品皮具", "奢侈品包"],
    }


# ── User input ─────────────────────────────────────────────────────────────────

def get_pipeline_inputs():
    print("\n=== Luxury Trend Intelligence Pipeline ===\n")

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY is not set.")
        print("Add it to your .env file:  ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    if sys.stdin.isatty():
        brand_input = input("Brand (e.g. Dior, Chanel, Louis Vuitton — press Enter for Dior): ").strip()
        brand = brand_input if brand_input else "Dior"

        city_input = input("Store city (e.g. Shanghai, Beijing, Chengdu — press Enter for Shanghai): ").strip()
        city = city_input if city_input else "Shanghai"

        scrape_input = input(
            "Scrape live XHS data now? (y/N — needs Chrome + DrissionPage installed): "
        ).strip().lower()
        do_scrape = scrape_input == "y"
    else:
        brand, city, do_scrape = "Dior", "Shanghai", False

    return brand, city, do_scrape


def brand_to_slug(brand: str) -> str:
    return brand.lower().strip().replace(" ", "_").replace("-", "_")


# ── Live XHS scraping ──────────────────────────────────────────────────────────

def scrape_live_xhs(brand: str, slug: str, scroll_times: int = 1) -> bool:
    """
    Run xhs_scraper_live.py for the brand — once for ready-to-wear keywords,
    once for leather goods keywords. Merges both runs into xhs_posts.json.

    Returns True if any posts were collected.
    """
    scraper_path = Path("module_1/xhs_scraper_live.py")
    if not scraper_path.exists():
        print("  [scraper] xhs_scraper_live.py not found — skipping.")
        return False

    # Check DrissionPage is available
    check = subprocess.run(
        [sys.executable, "-c", "import DrissionPage"],
        capture_output=True
    )
    if check.returncode != 0:
        print("  [scraper] DrissionPage is not installed.")
        print("  [scraper] Run:  pip3 install DrissionPage tqdm")
        print("  [scraper] Then re-run the pipeline and choose 'y' to scrape.")
        return False

    keywords_map = get_keywords(slug, brand)
    posts_path = Path("module_1/data/xhs_posts.json")
    all_posts = []

    env = os.environ.copy()
    env["DEFAULT_MODEL"] = DEFAULT_MODEL

    for category, keywords in keywords_map.items():
        kw_preview = "  ".join(keywords[:3])
        print(f"\n  [scraper] Category: {category}")
        print(f"  [scraper] Keywords: {kw_preview}")
        print(f"  [scraper] Scroll pages per keyword: {scroll_times}")
        if category == list(keywords_map.keys())[0]:
            print("  [scraper] NOTE: On first run ever, a Chrome window will open.")
            print("  [scraper] Scan the XHS QR code with your phone to log in.")
            print("  [scraper] After that, login is saved automatically.\n")

        try:
            subprocess.run(
                [sys.executable, "xhs_scraper_live.py",
                 "--keywords", *keywords,
                 "--times",    str(scroll_times),
                 "--category", category,
                 "--no-caption",    # skips OpenRouter image captioning; we use Anthropic
                 "--no-detail"],    # skips per-post detail pages; ~5x faster (remove for richer data)
                cwd="module_1",
                env=env,
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"  [scraper] Failed for {category} — continuing with other categories")
            continue

        if posts_path.exists():
            with open(posts_path, encoding="utf-8") as f:
                batch = json.load(f)
            all_posts.extend(batch)
            print(f"  [scraper] Collected {len(batch)} posts for '{category}'")

    if not all_posts:
        print("  [scraper] No posts collected — keeping existing xhs_posts.json")
        return False

    # Merge both category runs into a single file
    with open(posts_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    print(f"\n  [scraper] Done — {len(all_posts)} posts written to xhs_posts.json")
    return True


# ── Module 1 config ────────────────────────────────────────────────────────────

def write_module1_config() -> None:
    """Write run_config.json for module 1. brand=ALL so all posts pass through."""
    config_path = Path("module_1/data/run_config.json")
    config = {
        "brand": "ALL",
        "category": "",   # empty = no category filter; module 2 handles brand filtering
        "time_window": {"start_date": "2026-01-01", "end_date": "2026-03-31"},
        "max_posts": 100,
        "top_k_trends": 8,
        "min_posts_per_trend": 2,
        "llm": {"enabled": False, "model": DEFAULT_MODEL},
        "prompt": (
            "You are the decision engine for Module 1: XHS Trend Object Builder. "
            "Turn retrieved Xiaohongshu posts into reviewable Type-B trend objects. "
            "Work only with the provided posts. Identify semantically similar clusters by recurring "
            "themes, aesthetics, usage scenarios, product angles, behaviour patterns, or language signals. "
            "Ensure trend distinctness — merge overlapping clusters rather than forcing extra trends. "
            "For each trend generate: a concise label, a one-sentence summary, evidence from real posts, "
            "metrics (post_count, total_engagement), and confidence (low/medium/high). "
            "Confidence is high only when evidence is coherent and sufficient. "
            "Include ai_reasoning explaining why posts belong together. "
            "Never invent evidence not present in the retrieved posts."
        )
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  [config] Wrote module 1 run config")


# ── Module 1 → 2 handoff ───────────────────────────────────────────────────────

def copy_module1_to_module2() -> bool:
    src = Path("module_1/outputs/trend_objects.json")
    dst = Path("module_2/data/trend_objects.json")
    if not src.exists():
        print("  [handoff] No module 1 output — module 2 keeps its existing data")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    print(f"  [handoff] module_1/outputs/trend_objects.json → module_2/data/trend_objects.json")
    return True


# ── Subprocess runner ──────────────────────────────────────────────────────────

def run_module(module_dir, script_name, *args):
    print(f"\n--- Running {module_dir}/{script_name} ---")
    if not os.path.exists(os.path.join(module_dir, script_name)):
        print(f"Script not found. Skipping.")
        return False

    env = os.environ.copy()
    env["DEFAULT_MODEL"] = DEFAULT_MODEL

    try:
        subprocess.run(
            [sys.executable, script_name, *args],
            cwd=module_dir,
            env=env,
            check=True
        )
        print(f"--- Finished {module_dir}/{script_name} successfully ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"--- Error running {module_dir}/{script_name}: {e} ---")
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    brand, city, do_scrape = get_pipeline_inputs()
    slug = brand_to_slug(brand)

    print(f"\nPipeline: Brand={brand} | City={city} | Model={DEFAULT_MODEL}\n")

    # ── Step 0 (optional): live XHS scraping ───────────────────────────────────
    if do_scrape:
        print("── Live XHS Scraping ──────────────────────────────────────────────")
        scrape_live_xhs(brand, slug)
    else:
        print("  [scraper] Using existing xhs_posts.json  (enter 'y' at prompt to scrape live)")

    # ── Module 1: cluster posts → trend_objects.json ───────────────────────────
    write_module1_config()
    m1_ok = run_module("module_1", "xhs_trend_builder.py")

    # ── Handoff: M1 output → M2 input (only if M1 succeeded) ──────────────────
    if m1_ok:
        copy_module1_to_module2()
    else:
        print("  [handoff] Skipped — module 2 will use its existing trend data")

    # ── Module 2: filter + score trends for the brand ──────────────────────────
    run_module("module_2", "agent.py", "--brand", slug)

    # ── Module 3: trend briefs + persona matching ───────────────────────────────
    run_module("module_3/trend_brief_agent", "agent.py", "--brand", brand, "--city", city)

    print("\nPipeline complete.")
    print(f"Output → module_3/trend_brief_agent/trend_cards_{slug}_{city.lower()}.md")


if __name__ == "__main__":
    main()
