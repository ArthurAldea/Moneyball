---
phase: 05-dashboard-rebuild-shortlist-filters
plan: 02
subsystem: ui
tags: [streamlit, plotly, pandas, numpy, navy-theme, filters, scatter-plot]

# Dependency graph
requires:
  - phase: 05-01
    provides: test_app.py with 12 RED unit tests for filter functions and chart exports
  - phase: 04-advanced-scoring
    provides: scorer.py with _parse_age, run_scoring_pipeline, predicted_log_mv column

provides:
  - Complete single-page Streamlit dashboard with navy theme replacing cyberpunk 4-tab design
  - 6 sidebar filters (league, position, age, club, market value, season) with Reset Filters empty state
  - Shortlist table sorted by uv_score_age_weighted descending with row-click placeholder panel
  - UV scatter plot (scout_score x-axis, predicted_log_mv y-axis) with OLS FAIR VALUE LINE
  - Cross-league disclaimer (DASH-07) when >1 league selected
  - Pure-Python module exports: apply_filters, get_available_clubs, prepare_display_df, scatter_chart, should_show_disclaimer, NAVY_CSS

affects: [06-player-deep-profile]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "conftest.py Streamlit stub pattern: added column_config, divider, caption, container, st.stop noop, __getitem__ on _NoopCtx"
    - "Pure-Python module-level functions in app.py (not inside if __name__=='__main__') for pytest importability"
    - "apply_filters accepts all 6 params with defaults so tests can call with partial args"
    - "scatter_chart computes _mv_m inline from market_value_eur for hover; uses predicted_log_mv from scorer for y-axis"

key-files:
  created: []
  modified:
    - app.py
    - conftest.py

key-decisions:
  - "conftest.py st.stop() changed to true no-op (not SystemExit) so module-level st.stop() in empty-state branch does not prevent pure function exports from being importable in tests"
  - "conftest.py _NoopCtx.__getitem__ added: returns empty list for key='rows', _NoopCtx() otherwise — enables table_state['selection']['rows'] dict access"
  - "conftest.py column_config stub added as inner class module with TextColumn and NumberColumn — required for COLUMN_CONFIG module-level constant in app.py"
  - "apply_filters default arguments added (leagues=None, positions=None, etc.) so test_app.py can call with only the param being tested"
  - "scatter_chart receives filtered df with raw EUR, not display_df (which has EUR converted to M) — critical for correct _mv_m computation in hovertemplate"
  - "stHeader and stToolbar CSS added to NAVY_CSS to force navy background on Streamlit top bar (not covered by stAppViewContainer)"
  - "stDataFrame and stDataFrameResizable CSS added to remove cyberpunk-era table styling"
  - "Club filter default changed from available_clubs to [] (blank = all, via existing if-not guard)"
  - "prepare_display_df applies _parse_age and casts Age to Int64 so FBref years-days strings show as integers"

patterns-established:
  - "Pattern: conftest Streamlit stub must grow as app.py uses new st.* calls; always add missing stubs before each phase"
  - "Pattern: pure-Python functions exported at module level in app.py, Streamlit layout code below — enables pytest import without server"

requirements-completed:
  - FILTER-01
  - FILTER-02
  - FILTER-03
  - FILTER-04
  - FILTER-05
  - FILTER-06
  - DASH-01
  - DASH-02
  - DASH-03
  - DASH-04
  - DASH-05
  - DASH-06
  - DASH-07

# Metrics
duration: ~60min
completed: 2026-03-17
---

# Phase 05 Plan 02: Dashboard Rebuild — app.py Rewrite Summary

**Single-page navy Streamlit dashboard with 6 sidebar filters, ranked shortlist table, row-click placeholder panel, UV scatter plot with OLS line, and all 63 tests green**

## Performance

- **Duration:** ~60 min
- **Started:** 2026-03-17T05:59:30Z
- **Completed:** 2026-03-17
- **Tasks:** 2/2 complete (Task 1: implementation, Task 2: visual verification + post-review fixes)
- **Files modified:** 2

## Accomplishments
- Replaced the 4-tab cyberpunk dashboard (black/green/Share Tech Mono) entirely with professional navy single-page layout
- All 13 Phase 5 requirements (FILTER-01–06, DASH-01–07) implemented in app.py
- All 12 new test_app.py tests pass (GREEN); all 51 pre-existing tests continue to pass (63 total)
- conftest.py Streamlit stub extended with 3 missing attributes (column_config, divider, __getitem__) to support new app.py API surface
- 4 post-review visual fixes applied: top bar navy CSS, dataframe theme CSS, club filter blank default, age integer format via _parse_age

## Task Commits

Each task was committed atomically:

1. **Task 1: Write pure-Python module constants and functions** - `691cffe` (feat)
2. **Task 2 post-review: Top bar CSS, dataframe theme, club default, age integer format** - `795192f` (fix)

## Files Created/Modified
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/app.py` - Complete rewrite: navy CSS, 6 filters, shortlist table, scatter chart, pure-Python exports
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/conftest.py` - Extended Streamlit stub with column_config, divider, caption, container, st.stop noop, __getitem__

## Decisions Made
- `conftest.py st.stop()` changed to true no-op: the empty-state branch calls `st.stop()` at module level when the stub returns empty DataFrame; the old `_StopExecution(0)` (SystemExit subclass) was caught by `except BaseException` in test_app.py, setting `_APP_IMPORT_ERROR = 0` and blocking all 12 tests.
- `_NoopCtx.__getitem__` added to support `table_state["selection"]["rows"]` dict-style access that app.py uses for row selection.
- `conftest.py column_config` inner class stub added; app.py defines `COLUMN_CONFIG` at module level using `st.column_config.TextColumn` and `st.column_config.NumberColumn`.
- `apply_filters` default args added so test calls like `apply_filters(df, leagues=["EPL"])` work without passing all 6 params.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] conftest.py missing st.column_config attribute**
- **Found during:** Task 1 (first test run)
- **Issue:** app.py COLUMN_CONFIG constant uses `st.column_config.TextColumn` and `st.column_config.NumberColumn` at module level; conftest stub did not include `column_config`
- **Fix:** Added `_ColumnConfigModule` inner class with TextColumn and NumberColumn stubs to conftest
- **Files modified:** conftest.py
- **Verification:** Subsequent test run cleared this error
- **Committed in:** 691cffe (Task 1 commit)

**2. [Rule 3 - Blocking] conftest.py missing st.stop() safety (SystemExit propagation)**
- **Found during:** Task 1 (second test run)
- **Issue:** Old conftest raised `_StopExecution(0)` (SystemExit subclass) from `st.stop()`; `except BaseException` in test_app.py caught it and set `_APP_IMPORT_ERROR = 0`, blocking all 12 tests
- **Fix:** Changed `st.stop = _stop_stub` to `st.stop = _noop` — module execution continues past empty-state branch in test context
- **Files modified:** conftest.py
- **Verification:** All 12 tests pass after this fix
- **Committed in:** 691cffe (Task 1 commit)

**3. [Rule 3 - Blocking] conftest.py missing st.divider, st.caption, st.container**
- **Found during:** Task 1 (iterative test runs)
- **Issue:** app.py calls `st.divider()`, `st.caption()`, `st.container()` at module level; stub raised AttributeError
- **Fix:** Added all missing stubs to `_make_streamlit_stub()`
- **Files modified:** conftest.py
- **Verification:** Tests pass after stub additions
- **Committed in:** 691cffe (Task 1 commit)

**4. [Rule 3 - Blocking] _NoopCtx not subscriptable for table_state["selection"]["rows"]**
- **Found during:** Task 1 (fourth test run)
- **Issue:** `st.dataframe()` returns `_NoopCtx()`; app.py accesses result via `table_state["selection"]["rows"]`; `_NoopCtx` lacked `__getitem__`
- **Fix:** Added `__getitem__` to `_NoopCtx`: returns `[]` when key is `"rows"`, `_NoopCtx()` otherwise
- **Files modified:** conftest.py
- **Verification:** All 12 tests pass; 63 total tests green
- **Committed in:** 691cffe (Task 1 commit)

**5. [Rule 1 - Bug] Top bar remained black instead of navy (post-review)**
- **Found during:** Task 2 visual verification (user review)
- **Issue:** Streamlit's stHeader and stToolbar elements not covered by NAVY_CSS — defaulted to black
- **Fix:** Added CSS for `[data-testid="stHeader"]` and `[data-testid="stToolbar"]` with `background-color: #0D1B2A !important`
- **Files modified:** app.py
- **Verification:** 63 tests pass; CSS present in NAVY_CSS string
- **Committed in:** 795192f

**6. [Rule 1 - Bug] Shortlist table rendered with residual cyberpunk styling (post-review)**
- **Found during:** Task 2 visual verification (user review)
- **Issue:** .stDataFrame and inner iframe/table not targeted by theme CSS
- **Fix:** Added CSS rules for .stDataFrame, [data-testid="stDataFrameResizable"], iframe, and table selectors
- **Files modified:** app.py
- **Verification:** 63 tests pass
- **Committed in:** 795192f

**7. [Rule 1 - Bug] Club filter defaulted to all clubs pre-selected (post-review)**
- **Found during:** Task 2 visual verification (user review)
- **Issue:** `default=available_clubs` pre-selected every club; spec requires blank start (blank = all via guard)
- **Fix:** Changed to `default=[]`; existing `if not sel_clubs: sel_clubs = available_clubs` guard already handled blank-means-all
- **Files modified:** app.py
- **Verification:** 63 tests pass
- **Committed in:** 795192f

**8. [Rule 1 - Bug] Age displayed as FBref years-days string instead of integer (post-review)**
- **Found during:** Task 2 visual verification (user review)
- **Issue:** prepare_display_df passed raw Age column (e.g. "28-150"); player profile panel also used raw value
- **Fix:** Applied _parse_age in prepare_display_df with Int64 cast; applied _parse_age in profile panel for age_display
- **Files modified:** app.py
- **Verification:** 63 tests pass
- **Committed in:** 795192f

---

**Total deviations:** 8 auto-fixed (4 Rule 3 blocking conftest stub gaps in Task 1; 4 Rule 1 visual bugs discovered in post-review Task 2)
**Impact on plan:** Task 1 fixes were test infrastructure; Task 2 fixes were cosmetic/correctness improvements from visual review. No scope creep.

## Issues Encountered
- The conftest.py Streamlit stub was written for the old 4-tab app.py API surface and needed 4 new stubs (Task 1).
- Visual review revealed 4 additional issues (top bar color, table theme, club default, age format) — all fixed in a single Task 2 commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dashboard is fully functional: navy theme, 6 filters, shortlist table, player profile panel, UV scatter, disclaimer, empty state.
- Phase 6 (Player Deep Profile) can replace the placeholder panel with a full deep profile using the existing row-click selection mechanism.
- FBref Cloudflare blocker (Phase 5.1) must be resolved before live data populates — test_data.csv in cache/ provides demo data.

---
*Phase: 05-dashboard-rebuild-shortlist-filters*
*Completed: 2026-03-17*
