---
phase: 04-advanced-scoring
plan: 01
subsystem: scoring
tags: [pandas, scikit-learn, tdd, per90, team-strength, fbref]

requires:
  - phase: 03-multi-league-expansion
    provides: build_dataset with multi-league FBref data and compute_per90s pipeline

provides:
  - Pres_p90 column in merged DataFrame (via SUM_STATS + PER90_STATS additions)
  - stats_defense Succ collision fixed (possession Succ no longer shadowed)
  - PILLARS_DF defense updated to include Pres_p90=0.10 (DF-only)
  - apply_team_strength_adjustment function in scorer.py (±10% for DF/GK by league position)
  - run_scoring_pipeline calls team strength adjustment before compute_scout_scores

affects:
  - 04-02 (league quality multipliers — called after team strength in pipeline)
  - 04-03 (similar players — uses adjusted per-90 stats)
  - 05-dashboard-rebuild (displays Pres_p90; uses Pres in DF defense pillar)

tech-stack:
  added: []
  patterns:
    - "TDD wave-0 stubs: xfail strict=True stubs committed first, replaced with real tests in RED then GREEN"
    - "Team strength adjustment: per-league, per-position; n_clubs derived dynamically from max(league_position)"
    - "stats_defense Succ always dropped at join time to prevent possession Succ collision"

key-files:
  created: []
  modified:
    - config.py
    - merger.py
    - scorer.py
    - test_merger.py
    - test_scorer.py

key-decisions:
  - "PILLARS_DF defense overrides _DEFENSE entirely — Pres_p90 added at 0.10 with redistributed weights (Tkl 0.30, Int 0.25, Blocks 0.20, DuelsWon 0.15); _DEFENSE shared by FW/MF unchanged"
  - "apply_team_strength_adjustment placed before compute_scout_scores in run_scoring_pipeline — applying after normalization would have zero effect"
  - "n_clubs derived dynamically from max(league_position) per league — handles 20-club and 18-club leagues without hardcoding"
  - "Pres_p90 excluded from GK adjustment (_GK_RATE_STATS) — only Save% and PSxG/SoT adjusted for GK"
  - "NaN league_position silently skipped — consistent with merger soft-fail pattern from Phase 2"

patterns-established:
  - "Rule 3 deviation: rapidfuzz not installed in venv; installed from requirements.txt before task 1"

requirements-completed:
  - SCORE-04

duration: 3min
completed: 2026-03-17
---

# Phase 4 Plan 01: Pres_p90 Pipeline + Team Strength Adjustment Summary

**Pres (pressures) added to aggregation/per-90 pipeline, stats_defense Succ collision fixed, and apply_team_strength_adjustment (±10% for DF/GK by league position) implemented and wired into run_scoring_pipeline before normalization**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T02:17:57Z
- **Completed:** 2026-03-17T02:21:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `"Pres"` to `SUM_STATS` and `PER90_STATS`; `compute_per90s` now produces `Pres_p90` column
- Fixed stats_defense Succ column collision by adding `"Succ"` to drop_cols at join time; `DrbSucc%` now correctly derived from possession Succ (not defense Succ)
- Updated `PILLARS_DF` defense key with `Pres_p90=0.10` and redistributed weights; `_DEFENSE` (shared by FW/MF) left unchanged
- Implemented `apply_team_strength_adjustment` in scorer.py: bottom-half DFs get +10% on 5 defensive stats, top-half DFs get -10%; GK adjusted on Save%/PSxG-SoT only; FW/MF attacking stats untouched; NaN positions skipped
- Wired team strength step into `run_scoring_pipeline` before `compute_scout_scores`
- 5 new tests added (2 merger, 3 scorer); full suite: 31 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 xfail stubs** - `69aff93` (test)
2. **Task 2: Config + Merger fixes (TDD)** - `2507b65` (feat)
3. **Task 3: apply_team_strength_adjustment (TDD)** - `d7d2ac7` (feat)

## Files Created/Modified

- `config.py` - Added `"Pres"` to `SUM_STATS` and `PER90_STATS`; updated `PILLARS_DF["defense"]` with `Pres_p90=0.10`
- `merger.py` - Added `"Succ"` to stats_defense `drop_cols` to prevent Succ column collision
- `scorer.py` - Added `apply_team_strength_adjustment` function and constants; wired into `run_scoring_pipeline`
- `test_merger.py` - Wave 0 stubs replaced with real tests for Pres_p90 and DrbSucc% collision
- `test_scorer.py` - Wave 0 stubs replaced with real tests for team strength adjustment (3 tests)

## Decisions Made

- `PILLARS_DF["defense"]` fully overrides `_DEFENSE` rather than spreading it — prevents accidental propagation of Pres_p90 to FW/MF defense pillars
- `apply_team_strength_adjustment` inserted before `compute_scout_scores` — after normalization it would have zero effect (normalization re-scales all values anyway)
- `n_clubs` derived dynamically as `max(league_position)` per league — handles EPL/LaLiga/SerieA (20) and Bundesliga/Ligue1 (18) correctly without config constants

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed rapidfuzz in venv**
- **Found during:** Task 1 pre-check (baseline test run)
- **Issue:** `rapidfuzz` and `scikit-learn` not installed in active venv — `merger.py` import failed with ModuleNotFoundError
- **Fix:** `pip install rapidfuzz scikit-learn statsmodels` from requirements.txt
- **Files modified:** venv only (not tracked)
- **Verification:** All 26 pre-existing tests passed after install
- **Committed in:** Not committed (venv state only)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking import)
**Impact on plan:** Required fix to run tests at all; no scope creep.

## Issues Encountered

None beyond the venv missing packages resolved via Rule 3.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pres_p90 available in all DF rows after build_dataset
- Team strength adjustment in pipeline; ready for Phase 4 Plan 02 (league quality multipliers, SCORE-05)
- 31 tests green; no blockers
