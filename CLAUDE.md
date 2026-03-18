# Project: Moneyball Efficiency Analysis
Bridges on-pitch performance and market valuation for 5-league players using position-specific scout scoring and UV regression.

## Tech Stack
- Data: FBref (scraped via Playwright + BeautifulSoup) + Transfermarkt (market values)
- Processing: pandas, numpy, scikit-learn (MinMaxScaler), rapidfuzz (name matching)
- UI: Streamlit + Plotly
- Environment: Python 3.11+ (venv)

## Business Logic Rules
1. Scrape 2 seasons: 2023-24 and 2024-25. 2025-26 excluded (mid-season).
2. Minimum 900 minutes per season to qualify (DATA-07). Cached CSVs contain only qualifying players.
3. Undervaluation: position-aware OLS regression on log10(market_value) ~ scout_score + position_dummies. UV Score = percentile rank of negative residual; 100 = most undervalued.
4. Scout score is pillar-based per position (FW/MF/DF/GK). All pillar stat weights sum to 1.0 per pillar so max score ≈ 100.
5. FBref tables are wrapped in HTML comments — always search Comment nodes via `_extract_fbref_table()`. Direct `soup.find("table", id=...)` returns None for most FBref tables.
6. Cache scraped data in `cache/` with 7-day TTL. Naming: `cache/fbref_{league}_{table}_{season}.csv`.
7. Rate limiting: randomized 3.5–6.0s delay between every FBref request (DATA-06). Serial requests only.
8. Exponential backoff on HTTP 429: wait 30s → 60s → 120s. Raise RuntimeError after third failed retry.
9. Name matching (Transfermarkt → FBref): exact → rapidfuzz WRatio ≥ 80 → WRatio ≥ 70 + club cross-check.
10. Output columns: Player, Club, Position, Scout Score, Market Value, UV Score, Value Gap.
11. `run_fbref_scrapers(leagues=None, seasons=None)` is the primary scraping entry point (Playwright-based).
12. Standings sourced from football-data.co.uk (plain HTTP, no Cloudflare). Used for SCORE-04 team strength adjustment.

## FBref Lit Migration (2025) — Available Stats
FBref's Lit migration stripped most advanced stats. Only these columns have data:
- **stats_standard**: Gls, Ast, Min (per-90 pre-computed in .1 cols, but those are dropped and re-derived)
- **stats_shooting**: Gls, Sh, SoT
- **stats_defense**: TklW, Int (only — Tkl, Blocks, Pres all gone)
- **stats_misc**: CrdY, CrdR, Fls, Fld, Crs, Int, TklW
- **stats_keeper**: GA, SoTA, Saves, Save%, CS, CS%
- **stats_passing / stats_possession / stats_gca**: effectively empty
- **GONE from FBref**: PrgC, PrgP, KP, SCA, Blocks, Pres, aerial duels (Won/Lost), pass completion (Cmp/Att)
- **xG, xA**: Now sourced from Understat (Phase 06.1) — scraped separately and merged by player name. xG_p90 and xA_p90 incorporated into FW/MF Attacking and Creation pillars.

## Pillar Model (post-Lit)
Position weights: FW 45/20/20/5/10, MF 20/30/25/15/10, DF 10/15/10/45/20, GK 70/20/5/3/2

| Pillar | Outfield stats used |
|--------|---------------------|
| Attacking | FW: xG_p90 (0.45) + SoT_p90 (0.35) + Ast_p90 (0.20); MF: xG_p90 (0.40) + Gls_p90 (0.35) + SoT_p90 (0.25); DF: Gls_p90 + Ast_p90 + SoT_p90 (unchanged) |
| Progression | FW/DF: Sh_p90 + Fld_p90 · MF: Crs_p90 + Fld_p90 · DF: Crs_p90 |
| Creation | FW/MF: xA_p90 (0.50) + Ast_p90 (0.30) + Crs_p90 (0.20); DF: Ast_p90 + Crs_p90 (unchanged) |
| Defense | Int_p90 + TklW_p90 |
| Retention | Fld_p90 |
| GK Shot Stopping | Save% |
| GK Workload | Saves_p90 |

## Deployment Instructions
- Local: `streamlit run app.py`
- Pre-populate cache: `python scraper.py` (uses Playwright — Chromium must be installed)
- Production: Streamlit Community Cloud (commit cache/ CSVs to avoid live scrape on cold start)
