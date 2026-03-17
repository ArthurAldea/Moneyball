---
phase: 05-dashboard-rebuild-shortlist-filters
plan: 01
subsystem: testing
tags: [pytest, streamlit, pandas, plotly, tdd, fixtures]

# Dependency graph
requires:
  - phase: 04-advanced-scoring
    provides: run_scoring_pipeline output schema (Player, Squad, Pos, Age, League, market_value_eur, scout_score, uv_score, uv_score_age_weighted, value_gap_eur, league_quality_multiplier, predicted_log_mv, similar_players, _season)
provides:
  - test_app.py with 12 RED unit tests covering FILTER-01–06, DASH-01, DASH-02, DASH-04–07
  - make_pipeline_df(n) fixture factory producing deterministic pipeline-schema DataFrames
  - conftest.py Streamlit stub enabling fast test collection from Streamlit app.py
affects:
  - 05-02 (Phase 5 Plan 02 — these tests become GREEN when app.py exports the functions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD RED phase: test contracts written before implementation
    - Streamlit stub in conftest.py using sys.modules injection for testable Streamlit apps
    - _require_app() guard pattern for lazy ImportError propagation in test files

key-files:
  created:
    - test_app.py
    - conftest.py
  modified: []

key-decisions:
  - "conftest.py Streamlit stub installed via sys.modules injection before app import — prevents module-level network calls during test collection"
  - "_StopExecution(SystemExit) raised by stubbed st.stop() so partially-loaded app.py exits cleanly; caught by BaseException in test_app.py"
  - "_require_app() guard in each test function propagates ImportError without blocking pytest collection"
  - "make_pipeline_df provided as both @pytest.fixture and standalone function for flexible test usage"
  - "scatter_chart test checks x=scout_score (not market_value_eur) and y=predicted_log_mv (<10) — specifying Phase 5 redesign axes"

patterns-established:
  - "Streamlit stub pattern: sys.modules injection + _StopExecution + schema-correct empty DataFrame for cached load functions"
  - "TDD RED scaffold: import wrapped in try/except BaseException with _require_app() guards"

requirements-completed:
  - FILTER-01
  - FILTER-02
  - FILTER-03
  - FILTER-04
  - FILTER-05
  - FILTER-06
  - DASH-01
  - DASH-02
  - DASH-04
  - DASH-05
  - DASH-06
  - DASH-07

# Metrics
duration: 27min
completed: 2026-03-17
---

# Phase 5 Plan 01: Test Scaffold Summary

**12 RED unit tests with make_pipeline_df fixture factory and Streamlit stub conftest — contracts for apply_filters, scatter_chart, NAVY_CSS, and three helper functions**

## Performance

- **Duration:** 27 min
- **Started:** 2026-03-17T05:29:32Z
- **Completed:** 2026-03-17T05:56:00Z
- **Tasks:** 1
- **Files modified:** 2 (test_app.py, conftest.py — both created)

## Accomplishments

- Created `test_app.py` with 12 failing unit tests (RED state) covering all Phase 5 filter, display, and chart requirements
- Created `conftest.py` with a Streamlit stub that prevents module-level FBref network calls during test collection, keeping pytest fast (0.12s collection, 0.24s execution)
- Established `make_pipeline_df(n)` as both a pytest fixture and standalone function producing a deterministic DataFrame matching the run_scoring_pipeline output schema exactly

## Task Commits

1. **Task 1: Write test_app.py — fixture factory + 12 failing unit tests** — `a8113bc` (test)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `/Users/ArthurAldea/ClaudeProjects/Moneyball/test_app.py` — 12 RED unit tests + make_pipeline_df fixture covering FILTER-01–06, DASH-01, DASH-02, DASH-04–07
- `/Users/ArthurAldea/ClaudeProjects/Moneyball/conftest.py` — Streamlit stub (sys.modules injection) enabling fast test collection from module-level Streamlit app.py

## Decisions Made

- **conftest.py Streamlit stub pattern:** Current `app.py` executes `load_data()` at module level inside a `with st.spinner(...)` block, which triggers live FBref scraping. Rather than modifying app.py (Plan 05-02's job), a conftest.py stub was created that (1) replaces `streamlit` in `sys.modules` before any test imports app, (2) wraps `@st.cache_data` to return an empty schema-correct DataFrame, and (3) makes `st.stop()` raise `_StopExecution(SystemExit)` which exits the module load cleanly.
- **_require_app() guard:** The `from app import` block is wrapped in `except BaseException` (to catch both `ImportError` and `_StopExecution`). Each test function calls `_require_app()` first which re-raises `ImportError` — this gives pytest exactly 12 collectible tests that all fail with a clear error message.
- **scatter_chart axes spec:** Tests assert x=scout_score and y=predicted_log_mv (log scale values < 10). This documents the Phase 5 redesign away from the current chart (x=market_value_eur, y=scout_score) — the contract for Plan 05-02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created conftest.py Streamlit stub to prevent module-level network hang**
- **Found during:** Task 1 (test_app.py creation and verification)
- **Issue:** `app.py` runs `load_data()` → `run_fbref_scrapers()` at module level during `import app`. This caused pytest collection to hang indefinitely making live FBref HTTP requests (403 errors). The plan assumed import would fail with `ImportError`, but the actual failure was a hang.
- **Fix:** Created `conftest.py` that injects a minimal Streamlit stub into `sys.modules["streamlit"]` before any test file imports `app`. The stub makes `@st.cache_data` return an empty schema-correct DataFrame so `load_data()` completes instantly. Added `_StopExecution(SystemExit)` from stubbed `st.stop()` to halt module loading cleanly when `df.empty` is detected.
- **Files modified:** `conftest.py` (new file)
- **Verification:** `pytest test_app.py --collect-only -q` completes in 0.12s; 12 tests collected; no network calls.
- **Committed in:** `a8113bc` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The conftest.py fix is essential for the plan's acceptance criteria ("test_app.py is importable and runnable via pytest with no StreamlitAPIException"). No scope creep.

## Issues Encountered

- `app.py` module-level Streamlit execution (data pipeline + sidebar rendering) made direct import hang. Resolved with conftest.py Streamlit stub (see Deviations above). This is a temporary fix — Plan 05-02 refactors app.py into pure-Python functions, making the stub unnecessary for the 12 new tests.

## Next Phase Readiness

- test_app.py is ready: 12 RED tests define exact contracts for Plan 05-02 implementation
- conftest.py stub will continue working after Plan 05-02 refactor (stub is backward-compatible)
- Existing 51 tests (test_scorer.py, test_merger.py, test_scraper.py) all pass — zero regression

---
*Phase: 05-dashboard-rebuild-shortlist-filters*
*Completed: 2026-03-17*
