# Project State

**Current Phase:** Phase 1 — FBref Scraper (EPL)
**Status:** In Progress — Plan 01-01 complete, Plan 01-02 next
**Last Updated:** 2026-03-16

## Project Reference
See: .planning/PROJECT.md
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | 🔄 In Progress (Plan 01-01 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | 🔲 Not Started |
| 3 | Multi-League Expansion | 🔲 Not Started |
| 4 | Advanced Scoring | 🔲 Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** 01-01 complete
**Next:** Plan 01-02 (FBref fetch functions — Wave 2, depends on 01-01)

## Accumulated Decisions

- **stats_gca added as 9th table:** Captures SCA (shot-creating actions) needed by SCORE-02 MF Progression in Phase 2 — avoids a re-scrape later.
- **FBREF_SEASONS = ["2023-24", "2024-25"]:** 2025-26 excluded — mid-season, incomplete data.
- **Cache naming convention (DATA-05):** `cache/fbref_{LEAGUE}_{table}_{season}.csv` — e.g. `cache/fbref_EPL_stats_standard_2024-25.csv`.
- **Season label format:** Short form `"2024-25"` used throughout; `build_fbref_url()` converts to long form `"2024-2025"` for FBref URLs internally.
- **Function stubs pattern:** `scrape_fbref_stat` / `run_fbref_scrapers` added as stubs in Plan 01-01 so `test_scraper.py` imports without error before Plan 01-02 implements them fully.
- **test_scraper.py converted to pytest:** Was a print-based script; now a proper pytest module with smoke tests. Future plans should add real test functions here.

## Notes
(empty)
