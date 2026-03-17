---
phase: 03-multi-league-expansion
plan: 03
subsystem: scorer
tags: [sklearn, MinMaxScaler, per-league, normalization, multi-league, UV-regression]

# Dependency graph
requires:
  - phase: 03-02
    provides: merger multi-league support with League column in build_dataset output
  - phase: 02-03
    provides: compute_efficiency (UV regression), compute_age_weighted_uv, run_scoring_pipeline
provides:
  - Per-league MinMaxScaler normalization in compute_scout_scores (SCORE-01)
  - Backward-compatible fallback when no League column present (Phase 2 callers unchanged)
  - 3 new scorer tests covering per-league normalization, UV full pool, and League column preservation
affects: [app, dashboard, phase-04, phase-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Outer per-league loop: for league in df["League"].unique()
    - League-isolated MinMaxScaler: fitted per league+position group, not across all leagues
    - UV regression remains unchanged: full pooled DataFrame (SCORE-06)

key-files:
  created: []
  modified:
    - scorer.py
    - test_scorer.py

key-decisions:
  - "compute_scout_scores outer loop over df['League'].unique() — MinMaxScaler fitted independently per league+position group"
  - "Backward-compat fallback: when League column absent, leagues_to_score = [None] and league_df = df (Phase 2 behavior)"
  - "compute_efficiency unchanged — UV regression on full pooled multi-league DataFrame (SCORE-06)"

patterns-established:
  - "Per-league normalization: df[df['League'] == league].copy() isolates each league before _score_group"
  - "Backward compatibility via column presence check: if 'League' not in df.columns"

requirements-completed: [DATA-01, DATA-04, DATA-05]

# Metrics
duration: 15min
completed: 2026-03-17
---

# Phase 3 Plan 03: Multi-League Scorer Summary

**Per-league MinMaxScaler normalization in compute_scout_scores; UV regression unchanged on full pool**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-03-17
- **Tasks:** 4 (stubs, implementation, tests, regression check)
- **Files modified:** 2

## Accomplishments
- Added outer `for league in df["League"].unique()` loop to `compute_scout_scores` so MinMaxScaler is fitted independently per league+position group (SCORE-01)
- Preserved full backward-compatibility: callers without League column (Phase 2 code) still work via `leagues_to_score = [None]` fallback
- Left `compute_efficiency` (UV regression) unchanged — it continues to operate on the full pooled DataFrame (SCORE-06)
- Implemented all 3 new scorer tests (none skipped): per-league normalization isolation, UV full pool, League column preservation through pipeline

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 test stubs** - `32c7e21` (test)
2. **Task 2: Per-league outer loop in compute_scout_scores** - `ab4d466` (feat)
3. **Task 3: Implement 3 new test functions** - `cd0fb3c` (test)
4. **Task 4: Full regression check** - verified inline (40 passed, 0 failures)

## Files Created/Modified
- `scorer.py` - compute_scout_scores now has outer per-league loop; all other functions unchanged
- `test_scorer.py` - 3 new Phase 3 tests implemented and passing

## Decisions Made
- **Per-league isolation:** MinMaxScaler for FW in La Liga never sees EPL FW stats — ensures top forward in each league scores near 100 regardless of cross-league absolute stat differences.
- **UV regression unchanged:** compute_efficiency fits on the full pooled DataFrame to allow cross-league undervaluation comparison (a cheap La Liga player can be compared against EPL norms).
- **Backward compat via column presence:** `if "League" not in df.columns` fallback means zero changes required for Phase 2 callers or tests that don't include League column.

## Deviations from Plan

None — implemented exactly as specified.

## Issues Encountered
None.

## User Setup Required
None.

## Next Phase Readiness
- Phase 3 complete: scraper (03-01), merger (03-02), scorer (03-03) all multi-league aware
- Full pipeline: run_fbref_scrapers → build_dataset → compute_scout_scores (per-league) → compute_efficiency (full pool) → compute_age_weighted_uv
- Ready for Phase 4: Advanced Scoring

---
*Phase: 03-multi-league-expansion*
*Completed: 2026-03-17*
