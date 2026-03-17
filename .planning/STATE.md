---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 2
status: in-progress
stopped_at: Phase 2 Plan 02-02 complete — ready for 02-03
last_updated: "2026-03-17T01:00:00.000Z"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 7
  completed_plans: 5
---

# Project State

**Current Phase:** 2
**Status:** In progress (Plan 02-02 complete)
**Last Updated:** 2026-03-17 (Plan 02-02 executed)

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 2 — Merger & Scorer Rewrite (EPL End-to-End)

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete (Plans 01-01, 01-02, 01-03 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | 🔄 In Progress (2/4 plans done) |
| 3 | Multi-League Expansion | 🔲 Not Started |
| 4 | Advanced Scoring | 🔲 Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** Phase 2, Plan 02-02 complete. Next: Plan 02-03 (Scorer Rewrite + Age-Weight)
**Next:** Execute Plan 02-03 — rewrite scorer.py with FBref columns, age-weight UV score

## Accumulated Decisions

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
- **Deprecated stubs kept (not deleted):** run_understat_scrapers and run_api_football_scrapers return empty dicts; removal deferred to Phase 2 when merger.py is rewritten.
- **merger.py compute_per90s guard:** Added empty-DataFrame and missing-Min-column checks so build_dataset({}, {}, pd.DataFrame()) does not crash in Phase 1.
- **app.py shows 0 players in Phase 1:** Expected and acceptable — stubs return {} so merger produces empty output. Phase 2 will rewire load_data to call run_fbref_scrapers.

## Progress
Phase 1: [████████████████████] 3/3 plans (100%) — Complete
Phase 2: [██████████░░░░░░░░░░] 2/4 plans (50%) — In Progress

## Session Continuity
Last session: 2026-03-17T01:00:00.000Z
Stopped at: Plan 02-02 complete (merger rewrite + standings scraper + 11 tests)
Resume file: .planning/phases/02-merger-scorer-rewrite-epl-end-to-end/02-03-PLAN.md

## Blockers/Concerns
- ⚠️ [Phase 2 / Plan 02-03] `scorer.py` still references old Understat/API-Football column names (`xGChain`, etc.) — rewrite pending in Plan 02-03. `app.py` still shows 0 players until 02-03 and 02-04 are complete.

