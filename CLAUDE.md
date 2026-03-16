# Project: Moneyball Efficiency Analysis
Bridges on-pitch performance and market valuation for EPL players using Modern Portfolio Theory-inspired scout scoring.

## Tech Stack
- Data: FBref (scraped via requests + BeautifulSoup) + Transfermarkt (market values)
- Processing: pandas, numpy, scikit-learn (MinMaxScaler), rapidfuzz (name matching)
- UI: Streamlit + Plotly
- Environment: Python 3.11+ (venv)

## Business Logic Rules
1. Scrape 2 seasons in Phase 1: 2023-24 and 2024-25. (2025-26 is mid-season and excluded until Phase 2 or later.)
2. Minimum 900 minutes per season to qualify (DATA-07). Filtering applied inside `scrape_fbref_stat` before caching — cached CSVs contain only qualifying players.
3. Undervaluation = scout_score / log10(market_value_eur). Higher = more undervalued.
4. Scout score is pillar-based (Attacking 30pts, Progression 25pts, Creation 20pts, Defense 15pts, Retention 10pts). Phase 2 will update pillar stat references from Understat columns to FBref columns.
5. FBref tables are wrapped in HTML comments — always search Comment nodes using `_extract_fbref_table()`. Direct `soup.find("table", id=...)` returns None for most FBref tables.
6. Cache scraped data in `cache/` with 7-day TTL. Naming: `cache/fbref_{league}_{table}_{season}.csv` (e.g. `cache/fbref_EPL_stats_standard_2024-25.csv`). Never re-scrape unnecessarily.
7. Rate limiting: randomized 3.5–6.0s delay between every FBref request (DATA-06). Serial requests only — do NOT parallelize FBref scraping.
8. Exponential backoff on HTTP 429: wait 30s → 60s → 120s. Raise RuntimeError after the third failed retry (DATA-06).
9. Name matching (Transfermarkt → FBref): exact first, then rapidfuzz WRatio >= 80 threshold.
10. Output must always show: Player, Club, Position, Scout Score, Market Value, UV Score, Value Gap.
11. `run_understat_scrapers()` and `run_api_football_scrapers()` are stub functions retained for app.py backward compatibility — they return empty dicts. They will be removed in Phase 2 when merger.py is rewritten.
12. `run_fbref_scrapers(leagues=None, seasons=None)` is the new primary scraping entry point. It scrapes all 9 tables for all configured leagues and seasons.

## Deployment Instructions
- Local: `streamlit run app.py`
- Pre-populate cache: `python scraper.py` (~80 seconds for EPL cold run — 9 tables × 2 seasons = 18 requests at 3.5–6.0s each)
- Production: Streamlit Community Cloud (commit cache/ CSVs to avoid live scrape on cold start)
- **Phase 1 note:** app.py will show 0 players / "NO TARGETS MATCH CURRENT FILTERS" until Phase 2 rewires load_data to use run_fbref_scrapers directly.
