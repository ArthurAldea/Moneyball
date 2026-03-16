---
phase: 01-fbref-scraper-epl
plan: 03
subsystem: scraper
tags: [fbref, requests, beautifulsoup, pandas, pytest, monkeypatch]

# Dependency graph
requires:
  - phase: 01-fbref-scraper-epl/01-01
    provides: config constants (FBREF_TABLES, FBREF_SEASONS, FBREF_BACKOFF_SEQUENCE, build_fbref_url)
  - phase: 01-fbref-scraper-epl/01-02
    provides: scrape_fbref_stat, _fbref_cache_path, _is_fresh, _fetch_with_backoff, _extract_fbref_table
provides:
  - run_fbref_scrapers(leagues, seasons) orchestrator with correct nested-dict return
  - Deprecated stubs for run_understat_scrapers and run_api_football_scrapers (app.py compat)
  - Full 9-test pytest suite covering cache, rate limiting, backoff, URL, table extraction, column presence, orchestration, cache naming, warm-cache speed
  - CLAUDE.md updated with Phase 1 FBref architecture rules
affects: [Phase 2 merger rewrite, app.py load_data rewire]

# Tech tracking
tech-stack:
  added: []
  patterns: [run_fbref_scrapers nested-dict return {league: {season: {table_type: DataFrame}}}, deprecation stubs returning empty dict for backward compat, monkeypatch-based no-network pytest pattern]

key-files:
  created: []
  modified:
    - scraper.py
    - test_scraper.py
    - merger.py
    - CLAUDE.md

key-decisions:
  - "run_fbref_scrapers returns {league: {season: {table_type: df}}} not {table_type: {season: df}} — league-first nesting matches Phase 3 multi-league expansion"
  - "merger.py compute_per90s guard added: short-circuit on empty DataFrame or missing Min column so build_dataset({}, {}, pd.DataFrame()) does not crash"
  - "Deprecated stubs kept in place (not deleted) — app.py imports them by name; removal deferred to Phase 2"

patterns-established:
  - "Deprecation stub pattern: replace function body with empty-dict return + print warning, keep function signature intact"
  - "No-network test pattern: monkeypatch requests.get + time.sleep + CACHE_DIR in tmp_path"

requirements-completed: [DATA-01, DATA-02, DATA-05, DATA-06, DATA-07]

# Metrics
duration: 25min
completed: 2026-03-16
---

# Plan 01-03: Multi-Table Orchestrator & Integration Summary

**run_fbref_scrapers orchestrator, deprecated Understat/API-Football stubs for app.py compat, and a 9-test no-network pytest suite covering the full Phase 1 scraper**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-16
- **Completed:** 2026-03-16
- **Tasks:** 4 (03-01, 03-02, 03-03, 03-04)
- **Files modified:** 4

## Accomplishments
- Implemented `run_fbref_scrapers(leagues, seasons)` with correct `{league: {season: {table_type: df}}}` nesting, replacing the wrong stub from Plan 01-01
- Stubbed `run_understat_scrapers` and `run_api_football_scrapers` to return empty dicts, preserving app.py import compatibility while retiring live API calls
- Replaced 5-test smoke suite with 9-test no-network pytest suite; all 9 pass in under 1 second
- Updated CLAUDE.md Business Logic Rules to reflect Phase 1 FBref architecture (900 min/season, 2-season scope, cache naming, rate limits, backoff)

## Task Commits

Each task was committed atomically:

1. **Task 03-01: run_fbref_scrapers orchestrator** - `60e0b14` (feat)
2. **Task 03-02: Stub retired scrapers + merger fix** - `825352c` (feat)
3. **Task 03-03: 9-test pytest suite** - `bcd641d` (test)
4. **Task 03-04: Update CLAUDE.md** - `9f95e6b` (docs)

## Files Created/Modified
- `scraper.py` - run_fbref_scrapers orchestrator, deprecated stubs, updated __main__ block
- `test_scraper.py` - Full 9-test suite replacing smoke tests
- `merger.py` - compute_per90s guard for empty DataFrame (Phase 1 compat fix)
- `CLAUDE.md` - Business Logic Rules updated for FBref architecture

## Decisions Made
- `run_fbref_scrapers` uses league-first nesting `{league: {season: {table_type: df}}}` rather than table-first — aligns with Phase 3 multi-league expansion where iterating by league is the natural outer loop.
- Kept deprecated functions in place (not deleted) because app.py imports them by name; function removal deferred to Phase 2 merger rewrite.

## Deviations from Plan

### Auto-fixed Issues

**1. [Blocking] merger.py compute_per90s crashed on empty DataFrame**
- **Found during:** Task 03-02 (verifying build_dataset({}, {}, pd.DataFrame()) acceptance criterion)
- **Issue:** `compute_per90s` did `df["Min"]` without checking if the DataFrame was empty or had that column — raised `KeyError: 'Min'` when called with the empty result of `aggregate_understat({})`
- **Fix:** Added early returns for `df.empty` and `"Min" not in df.columns` at top of `compute_per90s`
- **Files modified:** `merger.py`
- **Verification:** `build_dataset({}, {}, pd.DataFrame())` returns 0-row DataFrame without exception
- **Committed in:** `825352c` (part of Task 03-02 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary to satisfy the plan's acceptance criterion. No scope creep.

## Issues Encountered
None beyond the merger.py crash documented above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 1 complete: all 9 FBref tables configured, scrape_fbref_stat implemented, run_fbref_scrapers orchestrator in place, app.py backward compat preserved
- app.py will show 0 players until Phase 2 rewires load_data to call run_fbref_scrapers
- Phase 2 blocker: merger.py uses old Understat/API-Football column names (xGChain, GoalsConceded, etc.) — these must be remapped to FBref column names (PrgP, GA, Save%, etc.) in the merger rewrite

---
*Phase: 01-fbref-scraper-epl*
*Completed: 2026-03-16*
