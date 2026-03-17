---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 3
status: phase-2-complete
stopped_at: Phase 2 complete — all 4 plans done; ready for Phase 3 (Multi-League Expansion)
last_updated: "2026-03-17T02:25:00.000Z"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 7
  completed_plans: 7
---

# Project State

**Current Phase:** 2 complete → starting Phase 3
**Status:** Phase 2 fully complete (Plan 02-04 done)
**Last Updated:** 2026-03-17 (Plan 02-04 executed)

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 2 complete — ready for Phase 3 Multi-League Expansion

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete (Plans 01-01, 01-02, 01-03 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | ✅ Complete (4/4 plans done) |
| 3 | Multi-League Expansion | 🔲 Not Started |
| 4 | Advanced Scoring | 🔲 Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** Phase 2 complete. Next: Phase 3 (Multi-League Expansion)
**Next:** Execute Phase 3 — extend scraper and pipeline to La Liga, Bundesliga, Serie A, Ligue 1

## Accumulated Decisions

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

## Session Continuity
Last session: 2026-03-17T02:25:00.000Z
Stopped at: Plan 02-04 complete (app.py rewired; 28 tests passing; Phase 2 done)
Resume file: .planning/phases/03-multi-league-expansion/ (Phase 3 planning)

## Blockers/Concerns
- None. Phase 2 fully complete. Dashboard shows real EPL players via FBref pipeline.
