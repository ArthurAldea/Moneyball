---
phase: 03-multi-league-expansion
plan: 02
subsystem: merger
tags: [rapidfuzz, pandas, fuzzy-matching, market-values, transfermarkt, fbref]

# Dependency graph
requires:
  - phase: 03-01
    provides: scraper multi-league data layer with league-first nesting
  - phase: 02-02
    provides: match_market_values (Pass 1 exact + Pass 2 WRatio≥80), build_dataset, _aggregate_fbref_seasons
provides:
  - 3-pass TM matching in match_market_values (Pass 1 exact, Pass 2 WRatio≥80, Pass 3 WRatio 70-79 + club cross-check)
  - normalize_club() helper stripping FC/CF/AFC prefixes and suffixes
  - single_season boolean flag in _aggregate_fbref_seasons output
  - 4 new merger tests covering multi-league League column, per-league min-minutes, Pass 3 logic, and single_season flag
affects: [scorer, app, dashboard, phase-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - 3-pass fuzzy matching: exact → WRatio≥80 → WRatio≥70+club cross-check
    - Club name normalization strips FC/CF/AFC affixes before comparison
    - single_season flag computed post-aggregation from _season nunique per player

key-files:
  created: []
  modified:
    - merger.py
    - test_merger.py

key-decisions:
  - "Pass 3 requires club cross-check to prevent false positives at lower name similarity (70-79 WRatio)"
  - "tm_club_lookup is defensively empty ({}) when club_tm column absent — backward-compatible with legacy TM DataFrames"
  - "normalize_club strips FC, CF, AFC affixes (with/without dot) using word-boundary regex — avoids over-stripping in compound names"
  - "single_season flag computed from combined._season.nunique per player after aggregation — True means player appeared in only 1 season (caveat for dashboard Phase 5)"

patterns-established:
  - "Pass N matching: each pass iterates only over players still unmatched from prior passes"
  - "Club cross-check: normalize_club applied to both FBref Squad and TM club_tm before string equality comparison"
  - "Defensive column access: check column presence before dict(zip(df[col])) to avoid KeyError on missing optional columns"

requirements-completed: [DATA-01, DATA-04, DATA-05]

# Metrics
duration: 20min
completed: 2026-03-17
---

# Phase 3 Plan 02: Multi-League Merger Summary

**3-pass TM matching with club cross-check and single_season boolean flag for multi-league player aggregation**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-17T04:30:00Z
- **Completed:** 2026-03-17T04:50:00Z
- **Tasks:** 4 (stubs, implementation, tests, regression check)
- **Files modified:** 2

## Accomplishments
- Extended `match_market_values` with Pass 3: WRatio 70-79 + club name cross-check reduces NaN market values for non-English players
- Added `normalize_club()` helper that strips FC/CF/AFC affixes for robust cross-league club name comparison
- Added `single_season` boolean column to `_aggregate_fbref_seasons` output for Phase 5 dashboard caveat logic
- 4 new merger tests all passing — covering multi-league League column, per-league min-minutes filter, Pass 3 club matching, and single_season flag

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 4 Phase 3 stub tests** - `44c3892` (test)
2. **Task 2: Implement 3-pass TM matching and single_season flag** - `014efe1` (feat)
3. **Task 3: Implement all 4 new test functions** - `688582e` (test)
4. **Task 4: Full regression check** - verified inline (37 passed, 0 failures)

## Files Created/Modified
- `merger.py` - Added normalize_club helper, FUZZY_THRESHOLD_PASS3 import, Pass 3 in match_market_values, single_season flag in _aggregate_fbref_seasons
- `test_merger.py` - Added 4 new Phase 3 tests (all passing)

## Decisions Made
- **Pass 3 requires club cross-check:** At WRatio 70-79 name similarity there are too many false positives for multi-language player names; requiring club match prevents incorrect value attachments.
- **Defensive tm_club_lookup:** When `club_tm` column is absent (legacy TM DataFrames in tests), Pass 3 silently skips — maintains backward compatibility with all existing tests.
- **normalize_club strips FC/CF/AFC:** Word-boundary regex avoids over-stripping inside compound names like "Atletico Madrid CF" → "atletico madrid".

## Deviations from Plan

### Auto-fixed Issues

**1. [Defensive coding] Added guard for missing club_tm column**
- **Found during:** Task 2 verification
- **Issue:** `dict(zip(tm["_norm"], tm["club_tm"]))` raises KeyError when `club_tm` column absent — all 13 existing tests pass TM DataFrames without this column
- **Fix:** `tm_club_lookup = dict(zip(...)) if "club_tm" in tm.columns else {}`
- **Files modified:** merger.py
- **Verification:** All 13 pre-existing merger tests continue to pass
- **Committed in:** `014efe1` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (defensive column access guard)
**Impact on plan:** Necessary for backward compatibility. No scope creep.

## Issues Encountered
None beyond the club_tm defensive guard noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- merger.py now supports 5-league data with League column, per-league min-minutes, 3-pass TM matching, and single_season flag
- Ready for Plan 03-03: run_scoring_pipeline multi-league wiring and full end-to-end pipeline test
- single_season column will be available in Phase 5 dashboard for caveat display

---
*Phase: 03-multi-league-expansion*
*Completed: 2026-03-17*
