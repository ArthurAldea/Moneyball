---
phase: 06-player-deep-profile
plan: 01
subsystem: dashboard
tags: [filter, player-search, multi-row-selection, radar, similar-players, tdd]
dependency_graph:
  requires: []
  provides:
    - filter_by_name (app.py)
    - cap_selection (app.py)
    - get_profile_header (app.py)
    - build_radar_figure (app.py)
    - compute_percentile (app.py)
    - parse_similar_players (app.py)
    - multi-row selection on shortlist table
    - PLAYER SEARCH sidebar widget
  affects:
    - app.py sidebar layout (PLAYER SEARCH added above LEAGUE)
    - app.py shortlist table (single-row → multi-row)
    - app.py scatter_chart (highlighted_players parameter)
    - test_app.py (23 tests total, 11 new Phase 6 stubs)
tech_stack:
  added: [json (stdlib), plotly Scatterpolar radar chart]
  patterns:
    - TDD red-green cycle (test stubs first, implementation second)
    - Pure helper functions exported for test isolation
    - rank(pct=True, method='min') for percentile boundary correctness
key_files:
  created: []
  modified:
    - app.py
    - test_app.py
decisions:
  - "compute_percentile uses rank(method='min') to avoid boundary inflation when test value equals min of series"
  - "build_radar_figure strips 'margin' from NAVY_LAYOUT dict before spreading to avoid duplicate kwarg conflict with explicit margin override"
  - "prepare_display_df() moved to before empty state check so filter_by_name can run on the prepared df"
metrics:
  duration: "4 minutes"
  completed_date: "2026-03-18"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 6 Plan 01: Wave 0 + FILTER-07 + Multi-Row Selection Summary

**One-liner:** TDD Wave 0 scaffolding for Phase 6 with PLAYER SEARCH sidebar filter, multi-row shortlist selection, and 6 pure helper functions (filter_by_name, cap_selection, get_profile_header, build_radar_figure, compute_percentile, parse_similar_players) all passing 23 tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 — Phase 6 test stubs + fixture enhancements | 2cd7b84 | test_app.py |
| 2 | FILTER-07 player search + multi-row selection + Phase 6 helpers | 9dadf02 | app.py |

## What Was Built

**Task 1 (TDD RED):** Extended `test_app.py` with 11 new Phase 6 test stubs spanning all pure helpers (`filter_by_name`, `cap_selection`, `get_profile_header`, `build_radar_figure`, `compute_percentile`, `parse_similar_players`). Updated `make_pipeline_df()` fixture to include Nation, score_* pillar columns, per-90 stats (Gls/Ast/SoT/Sh/Int/TklW/Fld/Crs/Saves_p90, Save%), and structured `similar_players` JSON for row 0.

**Task 2 (TDD GREEN):** Implemented all 6 Phase 6 pure helpers in `app.py`. Added `import json` and pillar config imports. Inserted PLAYER SEARCH sidebar widget above LEAGUE filter. Wired `filter_by_name()` onto `display_df` after `apply_filters()`. Moved `prepare_display_df()` call before empty state check. Added `"player_search"` to Reset Filters key deletion. Changed shortlist table to `selection_mode="multi-row"`. Replaced placeholder profile block with multi-row cap logic and session-state navigation hook. Extended `scatter_chart()` with `highlighted_players` parameter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NAVY_LAYOUT margin conflict in build_radar_figure**
- **Found during:** Task 2, test_radar_figure GREEN verification
- **Issue:** `NAVY_LAYOUT` dict contains `margin=dict(t=48, b=48, l=56, r=24)`. The plan's `build_radar_figure` code both spread `**NAVY_LAYOUT` and explicitly passed `margin=dict(t=32, b=32, l=32, r=32)`, causing `TypeError: got multiple values for keyword argument 'margin'`.
- **Fix:** Strip `margin` from the NAVY_LAYOUT copy before spreading: `radar_layout = {k: v for k, v in NAVY_LAYOUT.items() if k != "margin"}`, then pass explicit `margin=dict(t=32, b=32, l=32, r=32)` separately.
- **Files modified:** app.py
- **Commit:** 9dadf02

**2. [Rule 1 - Bug] compute_percentile boundary condition — value at min returned 25% not <=20%**
- **Found during:** Task 2, test_compute_percentile GREEN verification
- **Issue:** Plan specified `rank(pct=True)` (default `method='average'`). When `val=0.0` is appended to series `[0,25,50,75,100]`, two 0s share average rank 1.5/6 = 25%, failing `assert bot <= 20.0`.
- **Fix:** Use `rank(pct=True, method='min')` so the appended value gets the minimum (first) rank, yielding 1/6 ≈ 16.7% ≤ 20%.
- **Files modified:** app.py
- **Commit:** 9dadf02

## Success Criteria Verification

- [x] pytest test_app.py exits 0 with 23 tests collected and all passing
- [x] app.py contains `selection_mode="multi-row"` (line 629)
- [x] app.py contains `key="player_search"` in sidebar above LEAGUE filter (line 518)
- [x] app.py contains `"player_search"` in Reset Filters key deletion list (line 608)
- [x] All 6 Phase 6 pure helper functions importable from app.py
- [x] scatter_chart() accepts `highlighted_players` parameter (line 359)

## Self-Check: PASSED

Files confirmed present:
- app.py — modified (FOUND)
- test_app.py — modified (FOUND)

Commits confirmed:
- 2cd7b84 — test(06-01): Wave 0 — Phase 6 test stubs (FOUND)
- 9dadf02 — feat(06-01): FILTER-07 player search + multi-row selection (FOUND)
