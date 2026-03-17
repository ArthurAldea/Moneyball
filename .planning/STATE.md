---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 3
status: in_progress
stopped_at: Plan 03-03 executed (per-league MinMaxScaler normalization in compute_scout_scores; Phase 3 complete)
last_updated: "2026-03-17T06:00:00.000Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 10
  completed_plans: 9
---

# Project State

**Current Phase:** 4
**Status:** Phase 3 Complete — Ready for Phase 4 (Advanced Scoring)
**Last Updated:** 2026-03-17 (Plan 03-03 executed)

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 4 Advanced Scoring — Phase 3 complete, full 5-league pipeline ready

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete (Plans 01-01, 01-02, 01-03 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | ✅ Complete (4/4 plans done) |
| 3 | Multi-League Expansion | ✅ Complete (3/3 plans done) |
| 4 | Advanced Scoring | 🔲 Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** 03-03 complete. Phase 3 done.
**Next:** Phase 4 — Advanced Scoring

## Accumulated Decisions

- **[03-03] compute_scout_scores outer per-league loop:** MinMaxScaler fitted per league+position group independently — top forward in La Liga scores ~100 regardless of EPL forward distribution. Backward-compat fallback when League column absent.
- **[03-03] UV regression (compute_efficiency) unchanged:** Still operates on full pooled multi-league DataFrame (SCORE-06) — cross-league undervaluation comparison preserved.
- **[03-02] Pass 3 requires club cross-check:** At WRatio 70-79 name similarity there are too many false positives for multi-language player names; requiring club match prevents incorrect value attachments. normalize_club strips FC/CF/AFC affixes with word-boundary regex.
- **[03-02] tm_club_lookup defensively empty when club_tm absent:** When TM DataFrame lacks club_tm column (legacy test fixtures), Pass 3 silently skips — backward-compatible with all prior tests.
- **[03-02] single_season flag in _aggregate_fbref_seasons:** True when player appears in only 1 season (nunique==1 on _season). Available for Phase 5 dashboard caveat display.
- **[03-01] TM cache key uses season label as-is (2024-25 not 202425):** Matches FBref cache convention and is human-readable. run_tm_scrapers returns combined DataFrame with league_tm column; no cross-league deduplication — merger Pass 3 club cross-check disambiguates.
- **[03-01] run_tm_scrapers returns season + league_tm columns:** Enables Phase 3 merger to filter by league. Combined DataFrame not deduplicated across leagues — same player name can appear in multiple leagues after a transfer.
- **[03-01] TM_EPL_CLUBS_URL dead constant removed:** TM_LEAGUE_URLS in config.py is now the single source for all league club URLs (wettbewerb codes GB1, ES1, L1, IT1, FR1).
- **[03-01] FBREF_SEASONS filter in run_tm_scrapers:** Only scrapes TM for seasons with FBref coverage; skips 2025-26 mid-season data.
- **[02-04] Tab 3 leaderboard uses available_cols guard before rename:** `uv_score_age_weighted` silently skipped when absent — no crash if column missing.
- **[02-04] GK exploit label changed to Save% (.1f% format):** Consistent with scorer.py GK shot-stopping pillar definition (rate metric, not raw count).
- **[02-03] _parse_age handles FBref 'years-days' format:** Splits on '-' and takes first token; returns float(NaN) for unparseable values including None and 'N/A'.
- **[02-03] age-25 multiplier is 1.17, not 1.09:** Plan documentation had an error in the example values table; actual formula (log(29-age)/log(12) * 0.30 + 1.0) yields 1.167 at age 25, not 1.09. Tests corrected to match actual formula.
- **[02-03] run_scoring_pipeline signature changed to 2-arg (fbref_data, tm_data):** Old 3-arg (understat_data, api_data, tm_data) fully removed. app.py rewire completed in 02-04.
- **[02-02] _deduplicate_multiclub regex covers '2 Clubs' and '2 teams':** Pattern `r"^\d+\s+[Cc]lub|^\d+\s+[Tt]eam"` handles both FBref variants robustly across seasons.
- **[02-02] scrape_fbref_standings try/except fallback:** `_extract_fbref_table` raises `ValueError` on table-not-found; the standings function catches this and falls back to comment-node scan for resilience.
- **[02-02] build_dataset min-minutes scales by season count:** `MIN_MINUTES_PER_SEASON * len(league_data)` rather than hardcoded 1800 — correctly handles 1-season or 3-season inputs.
- **[02-02] attach_league_position fails soft:** All exceptions from `scrape_fbref_standings` caught; `league_position` set to NaN so pipeline never crashes on standings unavailability.
- **[02-01] DrbSucc% replaces DrbSucc_p90 in FW/DF Progression:** Rate metric (Succ/Att×100) preferred over raw count — quality over volume.
- **[02-01] MEAN_STATS=[] in aggregation:** All rate stats re-derived from summed raw counts post cross-season aggregation; never averaged across seasons.
- **[02-01] GK Shot Stopping: Save% (0.60) + PSxG/SoT (0.40):** Two complementary signals replace the single derived SavePct; PSxG/SoT rewards stopping harder shots.
- **stats_gca added as 9th table:** Captures SCA (shot-creating actions) needed by SCORE-02 MF Progression in Phase 2 — avoids a re-scrape later.
- **FBREF_SEASONS = ["2023-24", "2024-25"]:** 2025-26 excluded — mid-season, incomplete data.
- **Cache naming convention (DATA-05):** `cache/fbref_{LEAGUE}_{table}_{season}.csv` — e.g. `cache/fbref_EPL_stats_standard_2024-25.csv`.
- **Season label format:** Short form `"2024-25"` used throughout; `build_fbref_url()` converts to long form `"2024-2025"` for FBref URLs internally.
- **Function stubs pattern:** `scrape_fbref_stat` / `run_fbref_scrapers` added as stubs in Plan 01-01 so `test_scraper.py` imports without error before Plan 01-02 implements them fully.
- **test_scraper.py converted to full pytest suite:** Replaced 5 smoke tests with 9 no-network tests covering cache, rate limiting, backoff, URL construction, table extraction, column presence, orchestration, cache naming, and warm-cache speed.
- **pd.read_html(header=1) for FBref tables:** Skips the group-label row and uses stat-name row directly as column names; avoids fragile MultiIndex flattening.
- **xAG->xA rename at scrape time:** Applied inside scrape_fbref_stat for stats_standard so Phase 2 merger is agnostic of FBref's 2022-23 column rename.
- **scrape_fbref_stat prefix normalisation:** Accepts both "standard" and "stats_standard" — preserves test_scraper.py call signature without modification.
- **run_fbref_scrapers league-first nesting:** Returns `{league: {season: {table_type: df}}}` — league-first aligns with Phase 3 multi-league iteration pattern.

## Progress
Phase 1: [████████████████████] 3/3 plans (100%) — Complete
Phase 2: [████████████████████] 4/4 plans (100%) — Complete
Phase 3: [████████████████████] 3/3 plans (100%) — Complete

## Session Continuity
Last session: 2026-03-17T06:00:00.000Z
Stopped at: Plan 03-03 executed (per-league MinMaxScaler normalization; Phase 3 complete; 40 tests green)
Resume file: .planning/phases/03-multi-league-expansion/03-03-SUMMARY.md

## Blockers/Concerns
- None. Phase 3 complete; 40 tests green. Ready for Phase 4 (Advanced Scoring).
