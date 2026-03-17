---
phase: 03-multi-league-expansion
plan: 01
subsystem: scraper
tags: [fbref, transfermarkt, config, multi-league, cache, pytest]

# Dependency graph
requires:
  - phase: 02-merger-scorer-rewrite
    provides: run_fbref_scrapers league-first nesting, cache naming convention, scrape_fbref_stat
provides:
  - FBREF_LEAGUES with 5 entries (EPL, LaLiga, Bundesliga, SerieA, Ligue1)
  - TM_LEAGUE_URLS with 5 entries and correct wettbewerb codes
  - scrape_tm_season league param with league-keyed cache key
  - run_tm_scrapers loops all 5 leagues, returns DataFrame with league_tm column
  - FUZZY_THRESHOLD_PASS3 = 70 for Phase 3 name matching
  - 5 passing Phase 3 scraper tests covering URLs, cache naming, and orchestration
affects: [03-02-merger-multi-league, 03-03-scorer-multi-league]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - League-keyed TM cache naming: tm_values_{LEAGUE}_{season_label}.csv
    - run_tm_scrapers returns DataFrame with league_tm column (not deduplicated across leagues)
    - TM_LEAGUE_URLS dict in config.py as single source of truth for wettbewerb codes

key-files:
  created: []
  modified:
    - config.py
    - scraper.py
    - test_scraper.py

key-decisions:
  - "TM cache key uses season label as-is (2024-25) not compressed (202425) — maintains human-readability and matches FBref cache convention"
  - "run_tm_scrapers does NOT deduplicate across leagues — same player can appear in multiple leagues; Pass 3 club cross-check disambiguates in merger"
  - "run_tm_scrapers returns season + league_tm columns — enables Phase 3 merger to filter by league"
  - "TM_EPL_CLUBS_URL dead constant removed — TM_LEAGUE_URLS is now the single source for all league club URLs"
  - "FBREF_SEASONS filter in run_tm_scrapers — only scrapes TM for seasons with FBref coverage (skips 2025-26)"

patterns-established:
  - "Config expansion: new league keys added to both FBREF_LEAGUES and TM_LEAGUE_URLS simultaneously — both dicts must stay in sync"
  - "TM scraping: league parameter flows _get_tm_club_list → scrape_tm_season → run_tm_scrapers consistently"
  - "Test stubs (Wave 0) committed first, then implementations (Wave 1) — TDD pattern for scraper tests"

requirements-completed: [DATA-01, DATA-04, DATA-05]

# Metrics
duration: 20min
completed: 2026-03-17
---

# Plan 03-01: Multi-League Scraper Foundation Summary

**5-league FBref config expansion and Transfermarkt multi-league scraping with league-keyed cache naming, 14 green scraper tests**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-17T03:30:00Z
- **Completed:** 2026-03-17T03:50:00Z
- **Tasks:** 5
- **Files modified:** 3

## Accomplishments
- FBREF_LEAGUES expanded to 5 entries; run_fbref_scrapers automatically covers all 5 leagues without code change
- TM_LEAGUE_URLS added to config with correct wettbewerb codes (GB1, ES1, L1, IT1, FR1)
- scrape_tm_season and _get_tm_club_list refactored with league parameter and league-keyed cache keys
- run_tm_scrapers rewritten to loop all 5 leagues, returning combined DataFrame with league_tm column
- All 5 Phase 3 test stubs implemented and passing; full 33-test suite green (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs** - `fdaf923` (feat: 5 pytest.skip stubs)
2. **Task 2: Extend config.py** - `5df7043` (feat: FBREF_LEAGUES 5 entries, TM_LEAGUE_URLS, FUZZY_THRESHOLD_PASS3)
3. **Task 3: Extend scraper.py** - `947f4df` (feat: TM multi-league, league-keyed cache, remove TM_EPL_CLUBS_URL)
4. **Task 4: Implement 5 tests** - `1f703b0` (feat: replace stubs with real implementations)
5. **Task 5: Full test suite** - (verified inline — no code changes)

## Files Created/Modified
- `config.py` - FBREF_LEAGUES (1→5 entries), TM_LEAGUE_URLS (new), FUZZY_THRESHOLD_PASS3 (new)
- `scraper.py` - TM_LEAGUE_URLS import, _get_tm_club_list league param, scrape_tm_season league param + cache key, run_tm_scrapers rewrite, removed TM_EPL_CLUBS_URL
- `test_scraper.py` - 5 new Phase 3 tests (stubs then implementations)

## Decisions Made
- TM cache key retains season label as-is (`2024-25`) rather than compressed — consistent with FBref convention and human-readable
- run_tm_scrapers returns combined DataFrame without cross-league deduplication — merger's Pass 3 club cross-check handles disambiguation
- Dead constant `TM_EPL_CLUBS_URL` removed as part of the scraper refactor — TM_LEAGUE_URLS is the canonical source

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data layer foundation complete for all 5 leagues
- run_fbref_scrapers and run_tm_scrapers both support 5-league operation
- Ready for Plan 03-02: multi-league merger (build_dataset needs league-aware join)
- No blockers

---
*Phase: 03-multi-league-expansion*
*Completed: 2026-03-17*
