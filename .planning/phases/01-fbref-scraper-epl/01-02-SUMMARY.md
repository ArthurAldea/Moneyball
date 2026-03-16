---
phase: 01-fbref-scraper-epl
plan: "02"
subsystem: scraper
tags: [requests, beautifulsoup, pandas, fbref, html-comments, exponential-backoff, caching]

# Dependency graph
requires:
  - phase: 01-fbref-scraper-epl plan 01
    provides: _fbref_cache_path, _is_fresh, FBREF_BACKOFF_SEQUENCE, FBREF_LEAGUES, FBREF_TABLE_URL_SEGMENTS, build_fbref_url in config.py

provides:
  - _fetch_with_backoff(url, headers) — HTTP fetch with 30s/60s/120s 429 backoff
  - _extract_fbref_table(html, table_id) — comment-unwrapping HTML parser with flattened headers
  - scrape_fbref_stat(table_type, season_label, league) — primary scrape entrypoint with 7-day cache and 900-min filter
  - run_fbref_scrapers(league) — loops all FBREF_TABLES x FBREF_SEASONS

affects:
  - 01-03-PLAN (run_fbref_scrapers entry point and scraper integration)
  - Phase 2 merger (scrape_fbref_stat is the data source for FBref columns)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - cache-first: _is_fresh check before any network request
    - comment-unwrapping: BeautifulSoup Comment node fallback for FBref embedded tables
    - prefix normalisation: scrape_fbref_stat accepts both "standard" and "stats_standard"
    - xAG->xA rename: applied at scrape time for stats_standard to keep downstream code consistent

key-files:
  created: []
  modified:
    - scraper.py

key-decisions:
  - "Table extraction uses pd.read_html(header=1) to skip the group-label row and use stat-name row as columns — avoids MultiIndex complexity"
  - "scrape_fbref_stat normalises table_type prefix so test_scraper.py call with 'standard' works without changes"
  - "xAG renamed to xA inside scrape_fbref_stat for stats_standard — consistent column name regardless of season scraped"
  - "run_fbref_scrapers returns nested dict {table_type: {season: DataFrame}} rather than flat list"

patterns-established:
  - "Comment-unwrapping pattern: soup.find_all(string=lambda t: isinstance(t, Comment)) with table_id membership check"
  - "Min-filter pattern: comma-strip -> pd.to_numeric(errors=coerce) -> fillna(0) >= FBREF_MIN_MINUTES"

requirements-completed:
  - DATA-01
  - DATA-02
  - DATA-06
  - DATA-07

# Metrics
duration: 15min
completed: 2026-03-16
---

# Plan 02: FBref HTML Parser & Single-Table Scraper Summary

**HTTP fetch with 429 backoff, FBref comment-unwrapping HTML parser, and scrape_fbref_stat with 7-day cache and 900-minute player filter**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-16
- **Completed:** 2026-03-16
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- `_fetch_with_backoff` implements DATA-06 exponential backoff (30s/60s/120s) on HTTP 429, raising RuntimeError after three failures
- `_extract_fbref_table` unwraps FBref's comment-embedded tables using BeautifulSoup Comment nodes, flattens multi-level headers with `pd.read_html(header=1)`, and strips repeated header rows
- `scrape_fbref_stat` delivers cache-first logic, polite rate delay, 900-minute player filter (DATA-07), and xAG->xA normalisation for stats_standard

## Task Commits

Each task was committed atomically:

1. **Task 02-01: Implement _fetch_with_backoff** - `0fe08ab` (feat)
2. **Task 02-02: Implement _extract_fbref_table** - `add637f` (feat)
3. **Task 02-03: Implement scrape_fbref_stat** - `c0c3a35` (feat)

## Files Created/Modified
- `scraper.py` — Added `_fetch_with_backoff`, `_extract_fbref_table`, full `scrape_fbref_stat`, and `run_fbref_scrapers` implementations; replaced stubs; updated bs4 import to include `Comment`

## Decisions Made
- `pd.read_html(header=1)` chosen over manual MultiIndex flattening — cleaner and handles FBref's group-label row without fragile column index manipulation
- `scrape_fbref_stat` accepts bare prefix `"standard"` and normalises to `"stats_standard"` internally — preserves test_scraper.py call without modification
- xAG renamed to xA at scrape time (not at merge time) — keeps Phase 2 merger code agnostic of FBref's 2022-23 column rename

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three FBref primitives are implemented and tested; `run_fbref_scrapers` is ready to drive bulk scraping
- Plan 01-03 can now build on `scrape_fbref_stat` and `run_fbref_scrapers` to populate the full cache and wire the entry point into `__main__`

---
*Phase: 01-fbref-scraper-epl*
*Completed: 2026-03-16*
