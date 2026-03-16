---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 2
status: planning
stopped_at: Phase 2 context gathered
last_updated: "2026-03-16T03:56:26.737Z"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
---

# Project State

**Current Phase:** 2
**Status:** Ready to plan
**Last Updated:** 2026-03-16 (Plan 01-03 complete)

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 2 — Merger & Scorer Rewrite (EPL End-to-End)

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete (Plans 01-01, 01-02, 01-03 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | 🔲 Not Started |
| 3 | Multi-League Expansion | 🔲 Not Started |
| 4 | Advanced Scoring | 🔲 Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** 01-03 complete — Phase 1 fully done
**Next:** Phase 2 — Merger & Scorer Rewrite (EPL End-to-End)

## Accumulated Decisions

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
[████████████████████] 3/3 plans (100%) — Phase 1 complete

## Session Continuity
Last session: 2026-03-16T03:56:26.727Z
Stopped at: Phase 2 context gathered
Resume file: .planning/phases/02-merger-scorer-rewrite-epl-end-to-end/02-CONTEXT.md

## Blockers/Concerns
- ⚠️ [Phase 2] `merger.py` uses old Understat/API-Football column names (`xGChain`, `GoalsConceded`, etc.) — must be remapped to FBref columns (`PrgP`, `GA`, `Save%`) before scoring pipeline runs. `app.py` shows 0 players until this is resolved.

