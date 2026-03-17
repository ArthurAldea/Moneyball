---
phase: 02-merger-scorer-rewrite-epl-end-to-end
plan: 04
subsystem: ui, testing
tags: [streamlit, fbref, scorer, merger, pytest]

# Dependency graph
requires:
  - phase: 02-merger-scorer-rewrite-epl-end-to-end/02-03
    provides: run_scoring_pipeline 2-arg signature (fbref_data, tm_data); uv_score_age_weighted column

provides:
  - app.py wired to run_fbref_scrapers + run_scoring_pipeline(fbref_data, tm_data)
  - All Wave 4 merger integration tests implemented (no stubs remain)
  - Dashboard shows FBref-sourced EPL players with age-adjusted UV scores

affects: [03-multi-league-expansion, 05-dashboard-rebuild]

# Tech tracking
tech-stack:
  added: []
  patterns: [load_data calls run_fbref_scrapers + run_scoring_pipeline with 2-arg; Tab 3 always slices available_cols before renaming]

key-files:
  created: []
  modified: [app.py, test_merger.py]

key-decisions:
  - "Tab 3 leaderboard uses available_cols guard before rename so uv_score_age_weighted is shown when present but absent columns are silently skipped."
  - "GK exploit label changed to Save% (rate, not raw count) — consistent with scorer.py GK shot-stopping pillar."

patterns-established:
  - "load_data pattern: run_fbref_scrapers() → run_tm_scrapers() → run_scoring_pipeline(fbref_data, tm_data)"
  - "Integration tests for merge_fbref_tables use partial season_data dicts to verify missing-table NaN fill."

requirements-completed: [SCORE-01, DATA-03]

# Metrics
duration: 15min
completed: 2026-03-17
---

# Phase 2 Plan 04: app.py Rewire & Wave 4 Integration Tests Summary

**Streamlit dashboard fully wired to FBref pipeline: run_fbref_scrapers → run_scoring_pipeline(fbref_data, tm_data), with 13/13 merger tests passing and zero stubs remaining.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-17T02:10:00Z
- **Completed:** 2026-03-17T02:25:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- app.py load_data rewired to call `run_fbref_scrapers()` and `run_scoring_pipeline(fbref_data, tm_data)` — no legacy Understat/API-Football imports remain
- Tab 3 leaderboard now includes `uv_score_age_weighted` column (renamed "AGE-ADJ UV")
- GK player card shows `Save%` (rate metric) instead of `Saves_p90` (raw count)
- Wave 4 integration tests implemented: `test_nine_table_join_missing_table` and `test_prgc_source_is_possession` replace pytest.skip stubs
- Full test suite: 28 passed, 0 failed, 0 skipped across test_scorer.py, test_merger.py, test_scraper.py

## Task Commits

1. **Task 1: Rewire app.py load_data and remove dead imports** - `ba3d390` (feat)
2. **Task 2: Implement Wave 4 integration tests in test_merger.py** - `bcc08c1` (test)
3. **Task 3: Run complete test suite + static import check** — verified inline, no additional commit required

## Files Created/Modified

- `app.py` - load_data uses FBref pipeline; sidebar labels updated; GK stat = Save%; Tab 3 includes uv_score_age_weighted
- `test_merger.py` - Wave 4 tests implemented (no stubs remain); 13 tests total

## Decisions Made

- Tab 3 uses `available_cols` guard before column renaming, so `uv_score_age_weighted` is silently skipped when absent (e.g., during partial runs) without crashing
- GK exploit label updated to `Save%` with `.1f%` format for consistency with scorer.py GK pillar definition

## Deviations from Plan

None — plan executed exactly as written. Note: total test count is 28, not 27 as predicted in the plan (test_merger.py has 13 tests including `test_standings_scraper_caches` from plan 02-02, not 12). All 28 pass.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 2 is fully complete (4/4 plans done)
- Dashboard now shows real EPL players via FBref pipeline
- Ready to start Phase 3: Multi-League Expansion (add La Liga, Bundesliga, Serie A, Ligue 1)

---
*Phase: 02-merger-scorer-rewrite-epl-end-to-end*
*Completed: 2026-03-17*
