---
phase: 02-merger-scorer-rewrite-epl-end-to-end
plan: 02
status: complete
completed: "2026-03-17"
commits: 3
tests_added: 11
tests_passing: 11
tests_skipped: 2
---

# Plan 02-02 Summary — Merger Rewrite

## What Was Done

### Task 1: scrape_fbref_standings added to scraper.py
- Added `scrape_fbref_standings(league, season)` function after `run_fbref_scrapers`
- Reuses `_fbref_cache_path`, `_is_fresh`, `_fetch_with_backoff`, `_extract_fbref_table`
- Cache path: `cache/fbref_{league}_standings_{season}.csv` (7-day TTL)
- Primary strategy: try `_extract_fbref_table` with known table ID; fallback scans all comment nodes for any table with `Rk` + `Squad` columns
- Returns DataFrame with `Rk` (int) and `Squad` columns only; drops separator rows via `pd.to_numeric(..., errors='coerce')`

### Task 2: merger.py fully rewritten
Replaced the Understat/API-Football pipeline with FBref 9-table join pipeline.

**New functions:**
- `_deduplicate_multiclub(df)`: keeps `'2 Clubs'` summary row per player, drops per-club rows; handles `'2 teams'` edge case via regex
- `merge_fbref_tables(season_data)`: left-joins 9 FBref tables; handles all column collision rules:
  - `Att` in stats_possession → renamed `Att_drb` before join
  - `Won`/`Lost` in stats_misc → renamed `AerWon`/`AerLost`
  - `PrgC`/`PrgP` dropped from stats_standard (possession/passing canonical)
  - `xAG` dropped from stats_passing (already `xA` in stats_standard)
  - `Tkl.1` dropped from stats_defense (only total `Tkl` kept)
  - `Cmp%` from stats_keeper_adv dropped (launched-passes-only; passing Cmp% is authoritative)
- `_aggregate_fbref_seasons(fbref_league_data)`: sums raw counts across seasons via `SUM_STATS`; re-derives `Cmp%`, `DrbSucc%`, `DuelsWon%`, `Save%`, `PSxG/SoT` from summed counts
- `compute_per90s(df)`: derives `_p90` columns from raw counts + total `Min`; adds `DuelsWon_p90` alias from `AerWon`
- `extract_primary_position(df)`: `'DF,MF'` → `'DF'`
- `attach_league_position(df, league, season)`: joins standings via `scrape_fbref_standings`; multi-club players get `NaN`
- `build_dataset(fbref_data, tm_data)`: 2-arg pipeline (not 3-arg); league-first iteration; 1800-min filter (scaled by season count); current-season filter; per-90 derivation; league position; market value matching

**Kept unchanged:** `normalize_name`, `match_market_values`

**Removed:** `_aggregate_seasons`, `aggregate_understat`, `aggregate_api_football`, `merge_stat_sources`

### Task 3: test_merger.py — Wave 2 tests implemented
Replaced all 10 Wave 2 `pytest.skip` stubs with real implementations:
- `test_standings_scraper_caches`: mock HTTP + monkeypatch CACHE_DIR; asserts CSV written with Squad/Rk
- `test_multiclub_deduplication`: fixture with '2 Clubs' + per-club rows; asserts only summary kept
- `test_nine_table_join_full`: 4-table join with synthetic fixtures; asserts 2 rows, no duplicate columns, AerWon/AerLost/Att_drb/Tkl present
- `test_cross_season_aggregation`: 2-season fixture; asserts Min=4000, Gls=10
- `test_per90_derivation`: Min=1800 → Gls_p90 correct; Min=0 → NaN
- `test_drbsucc_rate_derivation`: arithmetic test; Att_drb=0 → NaN
- `test_duels_won_pct_derivation`: arithmetic test; total=0 → NaN
- `test_min_minutes_threshold_1800`: 1-season threshold = 900; Bob(1800) in, Charlie(500) out
- `test_current_season_filter`: Bob absent from 2024-25 → excluded despite total minutes
- `test_primary_position_extraction`: 'DF,MF'→'DF', 'GK'→'GK', 'FW,MF'→'FW'
- `test_league_position_attached`: Arsenal→1, '2 Clubs'→NaN

Wave 4 stubs remain as skips (`test_nine_table_join_missing_table`, `test_prgc_source_is_possession`).

## Test Results
- `pytest test_merger.py -x -q`: **11 passed, 2 skipped, 0 failed**
- `pytest test_scraper.py -x -q`: **9 passed, 0 failed** (no regression)

## Key Decisions Made
- `_deduplicate_multiclub` uses regex `r"^\d+\s+[Cc]lub|^\d+\s+[Tt]eam"` to handle both `'2 Clubs'` and `'2 teams'` variants
- `scrape_fbref_standings` uses try/except around `_extract_fbref_table` (it raises `ValueError` on miss) before falling back to comment-node scan
- `build_dataset` min-minutes threshold scales as `MIN_MINUTES_PER_SEASON * len(league_data)` (not hardcoded 1800) to handle 1-season or 3-season data correctly
- `attach_league_position` catches all exceptions from `scrape_fbref_standings` and falls back to NaN rather than crashing the pipeline

## Files Modified
- `scraper.py`: added `scrape_fbref_standings` (61 lines inserted)
- `merger.py`: full rewrite (270 lines added, 128 removed — net +142)
- `test_merger.py`: Wave 2 stubs replaced (147 lines added, 19 removed)
