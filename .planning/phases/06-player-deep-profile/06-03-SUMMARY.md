---
phase: 06-player-deep-profile
plan: 03
subsystem: ui
tags: [streamlit, plotly, radar-chart, comparison-mode, python]

# Dependency graph
requires:
  - phase: 06-02
    provides: render_single_profile(), COMPARISON_PALETTE, scatter_chart() with highlighted_players, comparison placeholder in main layout

provides:
  - render_comparison_profile() — overlaid radar, per-player stat columns, stacked similar players sections
  - Comparison-mode branch wired into main layout (placeholder removed)
  - Scatter chart x-axis Plotly rangeslider embedded below chart
  - Y-axis range control as two sliders in narrow left column beside scatter chart
  - Sidebar SCOUT SCORE RANGE and VALUE RANGE controls removed

affects: [06-player-deep-profile]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "COMPARISON_PALETTE[i % len(palette)] for distinct per-player colors in comparison mode"
    - "players_data list with one dict per selected player passed to build_radar_figure()"
    - "Stacked SIMILAR TO [NAME] sections per selected player in comparison mode"

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "render_comparison_profile() uses first player's Pos as peer median reference group for radar"
  - "Stat table uses ref_pos (first player's position) for pillar ordering; per-player percentile computed against each player's own position peer pool"
  - "n variable shadow bug avoided: renamed loop variable from n to pname in name_header_cells comprehension"
  - "scatter_chart x_range param removed — Plotly native rangeslider handles x-axis zoom embedded below chart"
  - "Y-axis range split into two sliders (mv_plot_max, mv_plot_min) in 4% column left of chart"

patterns-established:
  - "Comparison palette applied via palette[i % len(palette)] — works for 2 or 3 players"
  - "build_radar_figure() accepts any number of players_data dicts — unchanged from Plan 02"

requirements-completed: [PROFILE-06]

# Metrics
duration: 8min
completed: 2026-03-18
---

# Phase 6 Plan 03: Player Comparison View Summary

**render_comparison_profile() with overlaid radar polygons and per-player stat columns; scatter axis controls relocated from sidebar to chart area (Plotly rangeslider + y-axis column sliders)**

## Performance

- **Duration:** ~45 min (including checkpoint fix)
- **Started:** 2026-03-18T04:49:30Z
- **Completed:** 2026-03-18T05:30:00Z
- **Tasks:** 3 (2 auto + 1 continuation fix)
- **Files modified:** 1

## Accomplishments
- Implemented render_comparison_profile() with mini header cards, overlaid radar, per-player stat columns, and stacked similar players
- Replaced comparison-mode placeholder (Plan 02 st.caption stub) with full render_comparison_profile() call
- Relocated scatter chart axis controls from sidebar to chart area: x-axis uses Plotly native rangeslider; y-axis uses two sliders in a 4% column beside the chart
- Full test suite (23 app tests) remains green after all changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement render_comparison_profile() in app.py** - `7736656` (feat)
2. **Task 2: Wire render_comparison_profile into the main layout** - `ae5a1d4` (feat)
3. **Task 3 (continuation): Scatter axis sliders relocated to chart area** - `67ca989` (feat)

## Files Created/Modified
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/app.py` - Added render_comparison_profile(), wired into main layout comparison branch, removed sidebar axis sliders, added Plotly rangeslider + y-axis column sliders for scatter chart

## Decisions Made
- First player's position used as peer median reference group for radar (plan-specified)
- Stat table pillar order follows first player's position config; each player's percentile computed against their own position peer pool from full_df
- Minor fix: renamed loop variable `n` to `pname` in name_header_cells list comprehension to avoid shadowing the outer `n = len(active_players)` — deviation Rule 1 (auto-fixed bug)
- `scatter_chart()` `x_range` param removed entirely; Plotly `rangeslider` added to xaxis dict
- Y-axis range uses two sliders (`mv_plot_max`, `mv_plot_min`) in a `st.columns([0.04, 0.96])` layout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed variable shadowing in name_header_cells comprehension**
- **Found during:** Task 1 (render_comparison_profile implementation)
- **Issue:** Plan code used `n` as both the outer `len(active_players)` variable and the loop variable in the header cells comprehension (`for i, n in enumerate(player_names)`), causing the player name header cells to use the count integer instead of player name strings
- **Fix:** Renamed loop variable from `n` to `pname` in the comprehension
- **Files modified:** app.py
- **Verification:** pytest 23 app tests pass; grep confirms correct variable name
- **Committed in:** 7736656 (Task 1 commit)

---

**2. [User feedback at checkpoint] Scatter axis sliders moved from sidebar to chart area**
- **Found during:** Task 3 (checkpoint human-verify response)
- **Issue:** User specified sidebar sliders were wrong; x-axis should use Plotly rangeslider below chart, y-axis should use sliders in a left column
- **Fix:** Removed sidebar CHART-01/CHART-02 sliders; added `rangeslider` to xaxis dict; replaced single `st.plotly_chart()` call with `col_yslider, col_scatter = st.columns([0.04, 0.96])` layout with two stacked y-axis sliders
- **Files modified:** app.py
- **Verification:** 23 tests pass; scatter_chart() signature verified correct
- **Committed in:** 67ca989

---

**Total deviations:** 2 (1 auto-fixed Rule 1 bug + 1 user-directed correction at checkpoint)
**Impact on plan:** Both changes required for correctness and UX. No scope creep.

## Issues Encountered
- pytest required venv activation (`source venv/bin/activate`) — `nodriver` module not found outside venv. Normal project setup.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 6 complete — all 3 plans done
- All 6 success criteria met:
  1. 23 app tests green
  2. 2-3 row selection renders comparison mode with overlaid radar and per-player stat columns
  3. Each player has distinct COMPARISON_PALETTE color
  4. 4th row selection shows st.warning and caps at 3
  5. SIMILAR TO [NAME] stacked sections appear per selected player
  6. Scatter chart highlights all selected players with labeled markers
- Scatter chart axis controls now embedded in chart area (not sidebar)

---
*Phase: 06-player-deep-profile*
*Completed: 2026-03-18*

## Self-Check: PASSED
- app.py: FOUND
- Commit 7736656 (Task 1): FOUND
- Commit ae5a1d4 (Task 2): FOUND
- Commit 67ca989 (Task 3 continuation): FOUND
- 23/23 tests pass
