---
phase: 01
status: passed
created: 2026-03-16
---

# Phase 01 Verification

## Summary

All 10 must-have checks pass. The test suite runs clean (9/9 passed, exit 0). Every requirement ID from the plan frontmatter (DATA-01, DATA-02, DATA-05, DATA-06, DATA-07) is covered by both the implementation and the automated tests. No gaps were found.

## Must-Haves Check

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | `config.py` contains `FBREF_LEAGUES`, `FBREF_TABLES` (9 entries including `stats_gca`), `build_fbref_url()`, `FBREF_BACKOFF_SEQUENCE=[30,60,120]`, `FBREF_MIN_MINUTES=900` | ✅ | `config.py` lines 16–56: `FBREF_LEAGUES` dict with EPL; `FBREF_TABLES` list with all 9 entries ending in `stats_gca`; `FBREF_BACKOFF_SEQUENCE = [30, 60, 120]`; `FBREF_MIN_MINUTES = 900`; `build_fbref_url()` defined at line 70 |
| 2 | `scraper.py` contains `_fbref_cache_path()` returning `cache/fbref_{league}_{table}_{season}.csv` | ✅ | `scraper.py` lines 48–65: `_fbref_cache_path` builds `f"fbref_{league}_{table}_{season}.csv"` under `CACHE_DIR` |
| 3 | `scraper.py` contains `_fetch_with_backoff()` implementing 30s→60s→120s backoff, raising RuntimeError after 3 retries | ✅ | `scraper.py` lines 70–106: iterates `FBREF_BACKOFF_SEQUENCE + [None]`; sleeps on 429 using sequence values; raises `RuntimeError` when `delay is None` (fourth pass) |
| 4 | `scraper.py` contains `_extract_fbref_table()` that searches HTML Comment nodes and uses `pd.read_html(header=1)` | ✅ | `scraper.py` lines 109–170: Pass 1 is direct `soup.find`; Pass 2 iterates `soup.find_all(string=lambda t: isinstance(t, Comment))`; `pd.read_html(str(table), header=1)[0]` at line 157 |
| 5 | `scraper.py` contains `scrape_fbref_stat()` with cache-first, rate-limited, 900-minute filter, and xAG→xA rename | ✅ | `scraper.py` lines 175–276: `_is_fresh(path)` check at line 220 (cache-first); `random.uniform(FBREF_RATE_MIN, FBREF_RATE_MAX)` + `time.sleep` at lines 233–234 (rate limit); `df[df["Min"].fillna(0) >= FBREF_MIN_MINUTES]` at line 269 (900-min filter); `df.rename(columns={"xAG": "xA"})` at line 253 (xAG→xA rename) |
| 6 | `scraper.py` contains `run_fbref_scrapers()` iterating all FBREF_TABLES and FBREF_SEASONS | ✅ | `scraper.py` lines 279–327: three nested loops over `leagues`, `seasons`, and `FBREF_TABLES`; calls `scrape_fbref_stat(table_type, season, league)` for each combination |
| 7 | `run_understat_scrapers()` and `run_api_football_scrapers()` return `{}` (backward compatibility) | ✅ | `scraper.py` lines 407–418 and 555–566: both functions print a deprecation warning and `return {}` |
| 8 | `python -m pytest test_scraper.py -v` exits 0 with 9 passed | ✅ | Confirmed: `9 passed, 9 warnings in 0.51s` — all named tests collected and green |
| 9 | `build_fbref_url('EPL', 'stats_standard', '2024-25')` returns `https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats` | ✅ | Confirmed via `python -c "from config import build_fbref_url; print(build_fbref_url('EPL', 'stats_standard', '2024-25'))"` — output matches exactly |
| 10 | `CLAUDE.md` contains Phase 1 architecture rules (FBref, 900 min, 3.5–6.0s rate limit, etc.) | ✅ | `CLAUDE.md` rules 2, 5, 6, 7, 8, 11, 12 document: 900 min/season (DATA-07), Comment-node parsing, 7-day TTL + cache naming, 3.5–6.0s random delay, 30s→60s→120s backoff + RuntimeError, stub return values, and `run_fbref_scrapers` as primary entry point |

## Requirement Coverage

| Req ID | Description | Status |
|--------|-------------|--------|
| DATA-01 | EPL-only FBref scraper covering all required stat tables | ✅ Covered — `FBREF_LEAGUES` contains only EPL; `FBREF_TABLES` has 9 entries; `build_fbref_url` constructs correct EPL comp_id=9 URLs; tested by `test_url_construction` and `test_run_scrapers_epl` |
| DATA-02 | All required stat columns available for downstream use | ✅ Covered — `FBREF_TABLES` includes `stats_standard`, `stats_shooting`, `stats_passing`, `stats_defense`, `stats_possession`, `stats_misc`, `stats_keeper`, `stats_keeper_adv`, `stats_gca`; tested by `test_column_presence` and `test_run_scrapers_epl` |
| DATA-05 | Cache naming convention `cache/fbref_{league}_{table}_{season}.csv` and 7-day TTL | ✅ Covered — `_fbref_cache_path` enforces naming; `_is_fresh` enforces 7-day TTL; tested by `test_cache_fresh`, `test_cache_naming`, `test_cache_hit_is_fast` |
| DATA-06 | Rate limiting (3.5–6.0s) and exponential backoff (30→60→120s, RuntimeError after 3 retries) | ✅ Covered — `FBREF_RATE_MIN=3.5`, `FBREF_RATE_MAX=6.0`, `FBREF_BACKOFF_SEQUENCE=[30,60,120]` in `config.py`; `_fetch_with_backoff` implements backoff; `scrape_fbref_stat` applies random delay; tested by `test_rate_limit_delay` and `test_backoff_on_429` |
| DATA-07 | 900-minute per-season minimum filter applied before caching | ✅ Covered — `FBREF_MIN_MINUTES=900` in `config.py`; filter applied inside `scrape_fbref_stat` at line 269 before `df.to_csv`; tested by `test_column_presence` (fixture includes a 200-min player who should be filtered) |

## Human Verification Required

None. All automated checks passed. The only items from the original validation plan flagged as "manual-only" are live network checks (cold scrape populating CSVs, warm-cache timing with real files) — these are out of scope for this automated verification pass and are pre-existing documentation in `01-VALIDATION.md`.

## Gaps Found

None.
