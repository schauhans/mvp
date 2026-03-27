# Agent Pipeline (Modules 1–3)

This repository contains Modules 1 through 3 of the MVP Agent project. The pipeline runs end-to-end from XHS data scraping through trend filtering to CA-ready trend brief generation.

## Project Structure

- `module_1/`: XHS Trend Object Builder
- `module_2/`: Trend Relevance & Materiality Filter
- `module_3/`: CA Trend Brief Agent (with Client Persona Matching)
- `config.py`: Global configuration for API keys and default model
- `main.py`: Entry point — orchestrates modules 1 → 2 → 3 sequentially

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install DrissionPage tqdm  # required for live XHS scraping
   ```

2. **Configure API Keys:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to include:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   DEFAULT_MODEL=openai/gpt-4o-mini
   BRAND=Celine
   ```

## Running the Pipeline

```bash
python main.py
```

You will be prompted for:
- **Brand** — defaults to Celine
- **City** — defaults to Shanghai
- **Live scrape?** — answer `y` to scrape XHS in real time (requires Chrome), or `n` to use existing data

## Modules Overview

### Module 1: XHS Trend Object Builder
Scrapes Xiaohongshu search results for brand-relevant keywords and clusters posts into reusable Trend Objects (label / category / evidence / metrics / confidence).

### Module 2: Trend Relevance & Materiality Filter
Takes Module 1 trend objects and runs a two-stage filter: a deterministic pre-filter against the brand profile, then an LLM evaluation scoring each trend on freshness, brand fit, category fit, materiality, and actionability. Outputs a ranked shortlist of up to 5 trends.

Brand profiles are stored in `module_2/brand_profile_{brand}.json` — currently available for Celine, Dior, Chanel, Louis Vuitton, Bottega Veneta, Loewe, and Amiri.

### Module 3: CA Trend Brief Agent
Transforms the Module 2 shortlist into formatted Client Advisor trend cards. Each card includes:
- Trend overview and data signal with benchmarks
- Confidence rating with methodology explanation
- **Client persona matching** — automatically matches each trend to the most relevant client persona from the brand's persona file, including a "not for" filter to help CAs qualify clients
- Bilingual conversation starters (Chinese-first, English second)

Outputs both a Markdown file and a **styled HTML file** that can be opened in any browser or shared via a link for CAs to scroll through on their phones.

Persona files are stored in `module_3/trend_brief_agent/personas/{brand}_personas.json`.

## Global Configuration

```python
from config import OPENROUTER_API_KEY, DEFAULT_MODEL, BRAND
```
