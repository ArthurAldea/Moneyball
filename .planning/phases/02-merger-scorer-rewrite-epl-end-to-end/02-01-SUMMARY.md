---
phase: 02-merger-scorer-rewrite-epl-end-to-end
plan: 01
subsystem: config, testing
tags: [config, pytest, fbref, pillars, scorer]

# Dependency graph
requires:
  - phase: 01-fbref-scraper-epl
    provides: "FBref scraper producing 9 tables with FBref column names"
provides:
  - "Updated config.py with FBref-aligned pillar column names (PrgC_p90, DrbSucc%, PrgP_p90, SCA_p90, Save%, PSxG/SoT)"
  - "FBref-aligned SUM_STATS, PER90_STATS aggregation lists; MEAN_STATS cleared"
  - "test_merger.py with 14 Wave 0 stub tests covering all Phase 2 merger scenarios"
  - "test_scorer.py with 6 tests: 2 passing pillar-column validators + 4 stubs for Plan 02-03"
  - "MIN_MINUTES updated from 3000 to 1800 (2-season × 900 threshold)"
affects: [02-02, 02-03, 02-04, scorer.py, merger.py]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Wave 0 stubs: test functions skip with plan reference until implementing plan runs"]

key-files:
  created:
    - test_merger.py
    - test_scorer.py
  modified:
    - config.py

key-decisions:
  - "DrbSucc% (rate) replaces DrbSucc_p90 (count) in FW/DF Progression — quality over volume"
  - "MF Progression: PrgP_p90 (0.60) + SCA_p90 (0.40) replaces xGChain_p90"
  - "GK Shot Stopping: Save% (0.60) + PSxG/SoT (0.40) — two complementary signals replace single SavePct"
  - "UNDERSTAT_SUM and API_FOOTBALL_SUM removed; replaced with single FBref SUM_STATS list"
  - "MEAN_STATS set to [] — all rate stats re-derived from sums post-aggregation, never averaged across seasons"

patterns-established:
  - "Wave 0 stubs pattern: test file created before implementation with pytest.skip('stub — implemented in Plan XX-YY')"
  - "Acceptance: two non-stub tests test_scorer_new_pillar_columns and test_gk_shot_stopping_pillar pass immediately on config"

requirements-completed: [SCORE-02, SCORE-03]

# Metrics
duration: 15min
completed: 2026-03-17
---

# Plan 02-01: Config & Test Infrastructure Summary

**FBref pillar column names locked in config.py (PrgC_p90, DrbSucc%, PrgP_p90, SCA_p90, Save%, PSxG/SoT) with Wave 0 test stubs establishing the full merger+scorer test surface**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-17T00:00:00Z
- **Completed:** 2026-03-17T00:15:00Z
- **Tasks:** 3
- **Files modified:** 3 (config.py modified; test_merger.py, test_scorer.py created)

## Accomplishments
- All 5 pillar column remappings applied to config.py — no old Understat/API-Football column names remain
- FBref-aligned SUM_STATS, PER90_STATS, and empty MEAN_STATS established for Phase 2 merger aggregation
- 19 test functions collected across both test files with zero import errors; 11 pass immediately (2 new + 9 scraper regression)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update config.py pillar definitions to FBref columns** - `d898256` (feat)
2. **Task 2: Create Wave 0 test stubs for test_merger.py and test_scorer.py** - `1c0e082` (feat)
3. **Task 3: Run quick verification suite** - no commit (verification only)

## Files Created/Modified
- `config.py` - Updated PILLARS_FW/MF/DF progression stats, GK_PILLARS attacking stats, SUM_STATS, MEAN_STATS, PER90_STATS, MIN_MINUTES
- `test_merger.py` - 14 test stubs covering merger scenarios (Plans 02-02 and 02-04)
- `test_scorer.py` - 2 passing pillar-column tests + 4 stubs for age-weight tests (Plan 02-03)

## Decisions Made
- DrbSucc% (rate: Succ/Att×100) replaces DrbSucc_p90 in FW/DF Progression — rate metric preferred per CONTEXT.md
- MEAN_STATS cleared to [] because all rate stats will be re-derived from summed raw counts post cross-season aggregation
- Wave 0 stub pattern uses `pytest.skip("stub — implemented in Plan 02-XX")` to keep test files importable and future-plan-referenced

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- config.py pillar columns are fully FBref-aligned; Plan 02-02 can build merger.py against these names
- test_merger.py stubs provide the full test surface for Plan 02-02 to implement
- test_scorer.py stubs provide the test surface for Plan 02-03 age-weight implementation
- No blockers

---
*Phase: 02-merger-scorer-rewrite-epl-end-to-end*
*Completed: 2026-03-17*
