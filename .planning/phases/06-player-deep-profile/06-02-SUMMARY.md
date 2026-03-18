---
phase: 06-player-deep-profile
plan: 02
subsystem: ui
tags: [streamlit, plotly, scatter-chart, profile-view, radar, percentile]

# Dependency graph
requires:
  - phase: 06-01
    provides: filter_by_name, cap_selection, get_profile_header, build_radar_figure, compute_percentile, parse_similar_players, scatter_chart with highlighted_players, Phase 6 test scaffold

provides:
  - render_single_profile() — full single-player profile panel (header, radar, stat table, similar players)
  - _pct_bar_html() — HTML percentile bar helper (red/amber/green)
  - scatter_chart linear y-axis (€M) with x/y range sliders in sidebar
  - Stale-profile guard with st.info notice

affects: [06-03-comparison, any future profile/chart work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - OLS regression fit in log10(€M) space, back-converted to €M for linear y-axis display
    - Sidebar range sliders drive chart axis ranges via function params
    - Profile percentiles computed against full_df position peers, not filtered shortlist

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "scatter_chart y-axis switched from log to linear (€M) — cleaner tick labels, range sliders allow navigation"
  - "OLS regression stays in log10(€M) space — exponential fair-value curve shape preserved on linear axis"
  - "Sidebar SCOUT SCORE RANGE and VALUE RANGE sliders added below Season, above Refresh"
  - "_pct_bar_html colors: <33=red, 33-66=amber, >=66=green; bars compute against full_df same-position pool"
  - "Similar player click writes to session_state and calls st.rerun() for navigation"

patterns-established:
  - "Chart axis range driven by sidebar sliders — pass (min,max) tuples to chart function"
  - "profile percentile pool = full_df[full_df['Pos'] == pos], not filtered df"
  - "reset_filters loop deletes all slider keys including chart range keys"

requirements-completed:
  - PROFILE-01
  - PROFILE-02
  - PROFILE-03
  - PROFILE-04
  - PROFILE-05

# Metrics
duration: 25min
completed: 2026-03-18
---

# Phase 6 Plan 02: Player Profile Panel Summary

**Full single-player profile panel (header, radar chart vs peer median, per-90 stat table with red/amber/green percentile bars, similar player cards) plus scatter chart linear scale fix with sidebar x/y range sliders**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-18T~04:00Z
- **Completed:** 2026-03-18T~04:25Z
- **Tasks:** 3 (2 core + 1 checkpoint fix)
- **Files modified:** 2 (app.py, test_app.py)

## Accomplishments

- render_single_profile() renders header block, radar polygon vs peer median, per-90 stat table with percentile bars, and similar player cards with click navigation
- Scatter chart switched to linear y-axis with €M values — eliminates cramped log-scale tick labels
- Two sidebar range sliders (SCOUT SCORE RANGE, VALUE RANGE) let users zoom the scatter chart axes without refiltering the data
- Stale-profile guard shows st.info when session-state override player is filtered out of display_df

## Task Commits

1. **Task 1: Add _pct_bar_html helper and render_single_profile()** - `f92400c` (feat)
2. **Task 2: Wire render_single_profile into main layout + stale-profile guard** - `b6d24ff` (feat)
3. **Task 3 (checkpoint fix): Fix scatter axis — linear scale, x/y range sliders** - `515dc3a` (feat)

## Files Created/Modified

- `/Users/ArthurAldea/ClaudeProjects/Moneyball/app.py` — scatter_chart updated (linear y-axis, €M, x_range/y_range_m params); sidebar sliders added; render_single_profile and _pct_bar_html added; reset filters updated
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/test_app.py` — test_scatter_axes updated: asserts linear scale and €M y-values instead of log scale

## Decisions Made

- scatter_chart y-axis: linear scale with values in €M. OLS regression fit stays in log10(€M) space so the fair-value curve remains exponential — back-converted to €M for plotting on the linear axis.
- Sidebar sliders positioned after Season filter, before the Refresh button divider.
- Y-axis max computed from `full_df["market_value_eur"].max() / 1e7` rounded up to nearest 10 (reuses same formula as VALUE (€M) filter for consistency).
- test_scatter_axes updated to assert `yaxis.type != "log"` and that y-values are < 10,000 (confirming €M not raw EUR).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scatter_axes to match new linear-scale chart contract**
- **Found during:** Task 3 (scatter axis fix)
- **Issue:** test_scatter_axes asserted `yaxis.type == "log"` and y-values >= 1 (raw EUR). After switching to linear €M, the test would fail.
- **Fix:** Updated assertions to `yaxis.type != "log"` and `y < 10_000` (€M range check).
- **Files modified:** test_app.py
- **Verification:** pytest test_app.py passes (23/23)
- **Committed in:** `515dc3a` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test updated to match implementation change)
**Impact on plan:** Necessary update — test was asserting the old behavior that was explicitly changed. No scope creep.

## Issues Encountered

- Human reviewer reported y-axis jumbled/cramped tick labels on log scale — root cause was Plotly log scale tick density with the data range. Resolved by switching to linear scale with €M values and adding range sliders.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 Plan 03 (comparison view) can build on the established render_single_profile pattern
- scatter_chart now accepts x_range/y_range_m — comparison view can reuse this without changes
- All 23 tests passing

---
*Phase: 06-player-deep-profile*
*Completed: 2026-03-18*
