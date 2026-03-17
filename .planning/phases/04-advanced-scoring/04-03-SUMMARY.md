---
phase: 04-advanced-scoring
plan: "03"
subsystem: scoring
tags: [sklearn, cosine-similarity, similar-players, json, pandas, numpy]

# Dependency graph
requires:
  - phase: 04-02
    provides: "apply_league_quality_multiplier, uv_score_age_weighted adjusted for league quality"
  - phase: 04-01
    provides: "score_* pillar columns from compute_scout_scores"
provides:
  - "compute_similar_players function: top-5 style-similar players per player via cosine similarity"
  - "similar_players JSON column in run_scoring_pipeline output"
  - "4 SCORE-08 tests covering JSON structure, position scoping, self-exclusion, cross-league"
affects: [Phase 5 dashboard, Phase 6 player deep profile similar players panel (PROFILE-05)]

# Tech tracking
tech-stack:
  added: [sklearn.metrics.pairwise.cosine_similarity]
  patterns:
    - "NxN cosine similarity matrix computed per position group using vectorized sklearn; self excluded by setting diagonal to -1"
    - "Position group scoping: GK/FW/MF/DF iterated independently — no cross-position comparisons"
    - "JSON serialization of similar player entries with player/club/league/uv_score_age_weighted keys"

key-files:
  created: []
  modified:
    - scorer.py
    - test_scorer.py

key-decisions:
  - "cosine_similarity scoped per position group across all leagues (not per league) — style matching is global, only position is the boundary"
  - "Players with fewer than 2 group members get similar_players='[]' (graceful fallback)"
  - "top_k = min(5, n_candidates) handles small groups without crashing"
  - "similar_players called as the final step in run_scoring_pipeline, after league quality multiplier so uv_score_age_weighted is fully adjusted"

patterns-established:
  - "TDD RED/GREEN: xfail stubs committed first (Task 1), then replaced with real tests that fail before implementation, then implementation added"

requirements-completed: [SCORE-08]

# Metrics
duration: 7min
completed: 2026-03-17
---

# Phase 4 Plan 03: Similar Players Summary

**sklearn cosine similarity on 5 score_* pillar columns, position-group-scoped across all leagues, producing a top-5 similar_players JSON column wired as the final pipeline step**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T03:20:10Z
- **Completed:** 2026-03-17T03:26:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `compute_similar_players` to scorer.py: NxN cosine similarity matrix per position group (GK/FW/MF/DF), top-5 self-excluded, serialized as JSON with player/club/league/uv_score_age_weighted keys
- Wired `compute_similar_players` as the last step in `run_scoring_pipeline` after `apply_league_quality_multiplier`
- Added 4 SCORE-08 tests (column JSON validity, same position group, self-exclusion, cross-league) — all passing; total suite 37 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 xfail stubs for SCORE-08** - `58155a8` (test)
2. **Task 2: Implement compute_similar_players (TDD RED + GREEN)** - `3109b35` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD task had xfail stubs in Task 1 (RED), then real failing tests + implementation in Task 2 (GREEN)_

## Files Created/Modified
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/scorer.py` - Added `json` import, `cosine_similarity` import, `_SCORE_COLS` constant, `compute_similar_players` function; wired into `run_scoring_pipeline`
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/test_scorer.py` - Added `json` import, `_make_players` fixture helper, 4 SCORE-08 tests replacing xfail stubs

## Decisions Made
- cosine_similarity scoped per position group across all leagues — style matching is global, only position is the boundary (as specified in SCORE-08)
- `top_k = min(5, n_candidates)` handles position groups smaller than 6 players gracefully — empty list returned for groups < 2
- Similar players wired as the very last step in the pipeline so `uv_score_age_weighted` is already fully adjusted by league quality multiplier when serialized

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 4 Advanced Scoring is functionally complete: SCORE-04 (team strength), SCORE-05 (league quality multiplier), SCORE-08 (similar players) all implemented and tested — 37 tests green
- Phase 5 Dashboard Rebuild has `similar_players` JSON column available for display in the shortlist table or player cards
- Phase 6 Player Deep Profile has the `compute_similar_players` function and the PROFILE-05 similar players panel can consume `similar_players` column directly

---
*Phase: 04-advanced-scoring*
*Completed: 2026-03-17*

## Self-Check: PASSED
- SUMMARY.md exists at .planning/phases/04-advanced-scoring/04-03-SUMMARY.md
- scorer.py exists with compute_similar_players implemented
- test_scorer.py exists with 4 SCORE-08 tests
- Commit 58155a8 (xfail stubs): FOUND
- Commit 3109b35 (implementation): FOUND
