---
phase: 04-advanced-scoring
plan: "02"
subsystem: scoring
tags: [pandas, scikit-learn, league-quality, uv-score, coefficients]

# Dependency graph
requires:
  - phase: 04-01
    provides: apply_team_strength_adjustment, run_scoring_pipeline with age-weighted UV

provides:
  - LEAGUE_QUALITY_MULTIPLIERS dict in config.py (EPL 1.10 -> Ligue1 1.00)
  - apply_league_quality_multiplier function in scorer.py
  - league_quality_multiplier column on every player row in pipeline output
  - uv_score_age_weighted multiplied in-place by league coefficient after age-weighting step

affects:
  - 04-03-similar-players
  - 05-dashboard-rebuild
  - 06-player-deep-profile

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "League coefficient map in config.py (LEAGUE_QUALITY_MULTIPLIERS) consumed by scorer via import"
    - "DataFrame.map(dict).fillna(1.0) pattern for per-league coefficient lookup with unknown-league safety"
    - "In-place column multiplication: df[col] = df[col] * df[multiplier_col]"

key-files:
  created: []
  modified:
    - config.py
    - scorer.py
    - test_scorer.py

key-decisions:
  - "LEAGUE_QUALITY_MULTIPLIERS placed after TM_LEAGUE_URLS in config.py — grouped with league-level constants"
  - "Unknown/future leagues get multiplier 1.0 via fillna — pipeline never crashes on missing leagues"
  - "league_quality_multiplier stored as separate column (not discarded) for Phase 5 dashboard display"
  - "apply_league_quality_multiplier operates on a copy (df.copy()) — no mutation of caller DataFrame"

patterns-established:
  - "Per-league coefficient application: map(dict).fillna(1.0) with separate storage column"
  - "TDD RED/GREEN: xfail stubs committed first, real tests written (confirmed failing), then implementation"

requirements-completed:
  - SCORE-05

# Metrics
duration: 7min
completed: 2026-03-17
---

# Phase 4 Plan 02: League Quality Multiplier Summary

**LEAGUE_QUALITY_MULTIPLIERS dict (EPL 1.10 to Ligue1 1.00) applied to uv_score_age_weighted in-place via apply_league_quality_multiplier, wired into run_scoring_pipeline after age-weighting step (SCORE-05)**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-17T07:28:22Z
- **Completed:** 2026-03-17T07:35:02Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `LEAGUE_QUALITY_MULTIPLIERS` dict to `config.py` with UEFA coefficient-based values (EPL 1.10, LaLiga 1.08, Bundesliga 1.05, SerieA 1.03, Ligue1 1.00)
- Implemented `apply_league_quality_multiplier` in `scorer.py` — stores multiplier column, multiplies `uv_score_age_weighted` in-place, safe fallback for unknown leagues
- Wired function into `run_scoring_pipeline` after `compute_age_weighted_uv`; 33 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 xfail stubs for SCORE-05** - `6c4b50e` (test)
2. **Task 2: Implement SCORE-05 league quality multiplier (TDD)** - `b05f53a` (feat)

**Plan metadata:** _(docs commit follows)_

_Note: Task 2 is a TDD task — stubs committed in Task 1, real failing tests confirmed RED, then GREEN implementation in Task 2._

## Files Created/Modified
- `config.py` — Added `LEAGUE_QUALITY_MULTIPLIERS` dict (5 leagues, UEFA coefficient values)
- `scorer.py` — Added `LEAGUE_QUALITY_MULTIPLIERS` import, `apply_league_quality_multiplier` function, pipeline wiring
- `test_scorer.py` — Replaced xfail stubs with real `test_league_quality_multiplier_values` and `test_league_quality_multiplier_applied_in_place` tests

## Decisions Made
- `LEAGUE_QUALITY_MULTIPLIERS` placed after `TM_LEAGUE_URLS` in config.py — keeps all league-level constants grouped together
- Unknown/future leagues receive multiplier 1.0 via `fillna` — pipeline never crashes when a new league is added to FBref data before config is updated
- `league_quality_multiplier` stored as a separate column on the output DataFrame, not discarded after application — enables Phase 5 dashboard to display the coefficient for context
- Function operates on `df.copy()` — consistent with all other scorer pipeline functions; no mutation of caller's DataFrame

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. Tests ran clean on first GREEN attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SCORE-05 complete: every player row now carries `league_quality_multiplier` and `uv_score_age_weighted` reflects cross-league competitive difficulty
- ROADMAP success criterion 4 covered: EPL highest (1.10), Ligue1 lowest (1.00) among the five
- 33 tests green — ready for Plan 04-03 (similar players / SCORE-08)

---
*Phase: 04-advanced-scoring*
*Completed: 2026-03-17*
