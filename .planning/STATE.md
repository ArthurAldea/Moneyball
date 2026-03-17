---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 06
status: planning
stopped_at: Phase 05.1 verified — 63 tests green, VERIFICATION.md written
last_updated: "2026-03-17T20:00:00.000Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 17
  completed_plans: 17
---

# Project State

**Current Phase:** 06 (Phase 5.1 verified, ready for Phase 6)
**Status:** Phase 05.1 verified — 63 tests green
**Last Updated:** 2026-03-17 (Phase 05.1 verification complete)

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 4 Advanced Scoring — all 3 plans complete; SCORE-04, SCORE-05, SCORE-08 implemented

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete (Plans 01-01, 01-02, 01-03 done) |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | ✅ Complete (4/4 plans done) |
| 3 | Multi-League Expansion | ✅ Complete (3/3 plans done) |
| 4 | Advanced Scoring | ✅ Complete (3/3 plans done) |
| 5.1 | Fix FBref Scraping — Playwright Cloudflare bypass | ✅ Verified (2/2 plans, 63 tests green) |
| 5 | Dashboard Rebuild — Shortlist & Filters | 🔲 Not Started |
| 6 | Player Deep Profile | 🔲 Not Started |

## Current Position

**Plan:** Phase 05.1 verified.
**Next:** Phase 6 — Player Deep Profile (Phase 5 Dashboard Rebuild already complete)

## Accumulated Decisions

- **[04-03] compute_similar_players scoped per position group across all leagues:** Style matching is global (not per-league) — only position group is the boundary. GK/FW/MF/DF iterated independently with NxN cosine similarity matrix per group.
- **[04-03] similar_players wired as final pipeline step:** Called after apply_league_quality_multiplier so uv_score_age_weighted is fully adjusted when serialized into JSON entries.
- **[04-03] top_k = min(5, n_candidates) for small groups:** Players in groups with fewer than 2 members get similar_players="[]" — graceful fallback for edge cases.
- **[03-03] compute_scout_scores outer per-league loop:** MinMaxScaler fitted per league+position group independently — top forward in La Liga scores ~100 regardless of EPL forward distribution. Backward-compat fallback when League column absent.
- **[03-03] UV regression (compute_efficiency) unchanged:** Still operates on full pooled multi-league DataFrame (SCORE-06) — cross-league undervaluation comparison preserved.
- **[03-02] Pass 3 requires club cross-check:** At WRatio 70-79 name similarity there are too many false positives for multi-language player names; requiring club match prevents incorrect value attachments. normalize_club strips FC/CF/AFC affixes with word-boundary regex.
- **[03-02] tm_club_lookup defensively empty when club_tm absent:** When TM DataFrame lacks club_tm column (legacy test fixtures), Pass 3 silently skips — backward-compatible with all prior tests.
- **[03-02] single_season flag in _aggregate_fbref_seasons:** True when player appears in only 1 season (nunique==1 on _season). Available for Phase 5 dashboard caveat display.
- **[03-01] TM cache key uses season label as-is (2024-25 not 202425):** Matches FBref cache convention and is human-readable. run_tm_scrapers returns combined DataFrame with league_tm column; no cross-league deduplication — merger Pass 3 club cross-check disambiguates.
- **[03-01] run_tm_scrapers returns season + league_tm columns:** Enables Phase 3 merger to filter by league. Combined DataFrame not deduplicated across leagues — same player name can appear in multiple leagues after a transfer.
- **[03-01] TM_EPL_CLUBS_URL dead constant removed:** TM_LEAGUE_URLS in config.py is now the single source for all league club URLs (wettbewerb codes GB1, ES1, L1, IT1, FR1).
- **[03-01] FBREF_SEASONS filter in run_tm_scrapers:** Only scrapes TM for seasons with FBref coverage; skips 2025-26 mid-season data.
- **[02-04] Tab 3 leaderboard uses available_cols guard before rename:** `uv_score_age_weighted` silently skipped when absent — no crash if column missing.
- **[02-04] GK exploit label changed to Save% (.1f% format):** Consistent with scorer.py GK shot-stopping pillar definition (rate metric, not raw count).
- **[02-03] _parse_age handles FBref 'years-days' format:** Splits on '-' and takes first token; returns float(NaN) for unparseable values including None and 'N/A'.
- **[02-03] age-25 multiplier is 1.17, not 1.09:** Plan documentation had an error in the example values table; actual formula (log(29-age)/log(12) * 0.30 + 1.0) yields 1.167 at age 25, not 1.09. Tests corrected to match actual formula.
- **[02-03] run_scoring_pipeline signature changed to 2-arg (fbref_data, tm_data):** Old 3-arg (understat_data, api_data, tm_data) fully removed. app.py rewire completed in 02-04.
- **[02-02] _deduplicate_multiclub regex covers '2 Clubs' and '2 teams':** Pattern `r"^\d+\s+[Cc]lub|^\d+\s+[Tt]eam"` handles both FBref variants robustly across seasons.
- **[02-02] scrape_fbref_standings try/except fallback:** `_extract_fbref_table` raises `ValueError` on table-not-found; the standings function catches this and falls back to comment-node scan for resilience.
- **[02-02] build_dataset min-minutes scales by season count:** `MIN_MINUTES_PER_SEASON * len(league_data)` rather than hardcoded 1800 — correctly handles 1-season or 3-season inputs.
- **[02-02] attach_league_position fails soft:** All exceptions from `scrape_fbref_standings` caught; `league_position` set to NaN so pipeline never crashes on standings unavailability.
- **[02-01] DrbSucc% replaces DrbSucc_p90 in FW/DF Progression:** Rate metric (Succ/Att×100) preferred over raw count — quality over volume.
- **[02-01] MEAN_STATS=[] in aggregation:** All rate stats re-derived from summed raw counts post cross-season aggregation; never averaged across seasons.
- **[02-01] GK Shot Stopping: Save% (0.60) + PSxG/SoT (0.40):** Two complementary signals replace the single derived SavePct; PSxG/SoT rewards stopping harder shots.
- **stats_gca added as 9th table:** Captures SCA (shot-creating actions) needed by SCORE-02 MF Progression in Phase 2 — avoids a re-scrape later.
- **FBREF_SEASONS = ["2023-24", "2024-25"]:** 2025-26 excluded — mid-season, incomplete data.
- **Cache naming convention (DATA-05):** `cache/fbref_{LEAGUE}_{table}_{season}.csv` — e.g. `cache/fbref_EPL_stats_standard_2024-25.csv`.
- **Season label format:** Short form `"2024-25"` used throughout; `build_fbref_url()` converts to long form `"2024-2025"` for FBref URLs internally.
- **Function stubs pattern:** `scrape_fbref_stat` / `run_fbref_scrapers` added as stubs in Plan 01-01 so `test_scraper.py` imports without error before Plan 01-02 implements them fully.
- **test_scraper.py converted to full pytest suite:** Replaced 5 smoke tests with 9 no-network tests covering cache, rate limiting, backoff, URL construction, table extraction, column presence, orchestration, cache naming, and warm-cache speed.
- **pd.read_html(header=1) for FBref tables:** Skips the group-label row and uses stat-name row directly as column names; avoids fragile MultiIndex flattening.
- **xAG->xA rename at scrape time:** Applied inside scrape_fbref_stat for stats_standard so Phase 2 merger is agnostic of FBref's 2022-23 column rename.
- **scrape_fbref_stat prefix normalisation:** Accepts both "standard" and "stats_standard" — preserves test_scraper.py call signature without modification.
- **run_fbref_scrapers league-first nesting:** Returns `{league: {season: {table_type: df}}}` — league-first aligns with Phase 3 multi-league iteration pattern.
- [Phase 04-advanced-scoring]: LEAGUE_QUALITY_MULTIPLIERS placed after TM_LEAGUE_URLS in config.py; unknown leagues get 1.0 fallback via fillna; league_quality_multiplier stored as separate column for Phase 5 dashboard display
- [Phase 05]: conftest.py Streamlit stub installed via sys.modules injection — prevents module-level network calls during test collection for Streamlit apps
- [Phase 05]: _require_app() TDD guard pattern: import wrapped in BaseException handler, each test calls guard first — 12 RED tests collectible before any implementation
- [Phase 05]: conftest.py st.stop() changed to no-op: old SystemExit subclass was caught by BaseException in test_app.py, blocking all 12 tests
- [Phase 05]: _NoopCtx.__getitem__ added to support table_state['selection']['rows'] dict-style access in app.py row selection
- [Phase 05]: apply_filters default args added so tests can call with a single named param (e.g., leagues=[]) without passing all 6 args
- [Phase 05-02]: Club filter defaults to blank (empty list); blank = all via if-not guard — matches UX spec
- [Phase 05-02]: prepare_display_df applies _parse_age and casts Age to Int64 for clean integer display in shortlist table
- [Phase 05-02]: stHeader and stToolbar CSS targeted explicitly in NAVY_CSS to force navy top bar matching #0D1B2A background
- [Phase 05.1]: _do_playwright_get extracted as thin wrapper for test isolation; FBREF_HEADERS removed from imports after Playwright migration
- [Phase 05.1-02]: test_data.csv shim removed from load_data(); load_data() now unconditionally calls run_fbref_scrapers + run_tm_scrapers + run_scoring_pipeline; cache/test_data.csv deleted

## Progress
Phase 1: [████████████████████] 3/3 plans (100%) — Complete
Phase 2: [████████████████████] 4/4 plans (100%) — Complete
Phase 3: [████████████████████] 3/3 plans (100%) — Complete
Phase 4: [████████████████████] 3/3 plans (100%) — Complete
Phase 5.1: [████████████████████] 2/2 plans (100%) — Complete

## Session Continuity
Last session: 2026-03-17T19:25:00.000Z
Stopped at: Completed 05.1-02 — Removed test_data.csv shim from load_data()
Resume file: None

## Accumulated Context

### Roadmap Evolution
- Phase 5.1 inserted after Phase 5: Fix FBref scraping — replace requests with Playwright to bypass Cloudflare JS challenge (URGENT)

## Blockers/Concerns
- FBref now returns Cloudflare JS challenge (403) for all automated HTTP requests — scraper produces no data. Phase 5.1 will fix using Playwright headless browser.
