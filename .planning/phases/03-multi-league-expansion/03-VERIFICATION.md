---
phase: 3
status: passed
verified_at: 2026-03-17
---

# Phase 3 Verification

## Must-Haves Check

### Plan 03-01 Must-Haves

| Must-Have | Source Plan | Status | Evidence |
|-----------|-------------|--------|----------|
| config.py FBREF_LEAGUES contains exactly 5 entries: EPL, LaLiga, Bundesliga, SerieA, Ligue1 | 03-01 | ✅ verified | config.py lines 16–22: dict with exactly those 5 keys |
| config.py TM_LEAGUE_URLS contains exactly 5 entries with correct wettbewerb codes: GB1, ES1, L1, IT1, FR1 | 03-01 | ✅ verified | config.py lines 115–121: all 5 entries; URLs contain GB1, ES1, L1, IT1, FR1 respectively |
| scraper.run_fbref_scrapers() with no args returns dict with all 5 league keys | 03-01 | ✅ verified | scraper.py line 368: `leagues = list(FBREF_LEAGUES.keys())` when leagues=None; test_run_fbref_scrapers_all_leagues passes (confirmed 40/40) |
| scraper.run_tm_scrapers() with no args returns combined DataFrame across all 5 leagues | 03-01 | ✅ verified | scraper.py lines 776–812: loops TM_LEAGUE_URLS.keys() when leagues=None; test_run_tm_scrapers_multi_league passes |
| TM cache naming uses league-keyed convention: tm_values_{LEAGUE}_{season}.csv | 03-01 | ✅ verified | scraper.py line 734: `cache_key = f"tm_values_{league}_{season_label}"`; test_tm_cache_naming_league_keyed passes |
| scrape_tm_season accepts league parameter and uses it in cache key | 03-01 | ✅ verified | scraper.py line 733: `def scrape_tm_season(season_year: int, season_label: str, league: str = "EPL")` |
| test_scraper.py contains 5 new stub tests for multi-league scraping | 03-01 | ✅ verified | test_scraper.py lines 303–478: all 5 tests present and fully implemented (not stubs) |

### Plan 03-02 Must-Haves

| Must-Have | Source Plan | Status | Evidence |
|-----------|-------------|--------|----------|
| merger.match_market_values implements 3-pass TM matching: exact → WRatio≥80 → WRatio 70-79 + club cross-check | 03-02 | ✅ verified | merger.py lines 322–358: Pass 1 (exact map), Pass 2 (WRatio≥80), Pass 3 (WRatio≥70 + normalize_club cross-check) |
| merger._aggregate_fbref_seasons produces single_season boolean column | 03-02 | ✅ verified | merger.py lines 241–243: season_count computed, `grouped["single_season"] = grouped["Player"].map(season_count) == 1` |
| single_season=True when player appears in only 1 season; False when 2 seasons | 03-02 | ✅ verified | test_single_season_flag passes (bob → True, alice → False) |
| merger.build_dataset assigns League column for each league before concatenation | 03-02 | ✅ verified | merger.py line 405: `df["League"] = league` inside per-league loop; test_league_column_present_multi_league passes |
| test_merger.py contains 4 new tests: test_league_column_present_multi_league, test_per_league_min_minutes_filter, test_pass3_tm_matching, test_single_season_flag | 03-02 | ✅ verified | test_merger.py lines 332–485: all 4 tests present and fully implemented |
| all 4 new merger tests pass (not skipped) | 03-02 | ✅ verified | Full test suite: 40 passed, 0 failures (confirmed by running pytest) |

### Plan 03-03 Must-Haves

| Must-Have | Source Plan | Status | Evidence |
|-----------|-------------|--------|----------|
| scorer.compute_scout_scores has outer loop: for league in df['League'].unique() | 03-03 | ✅ verified | scorer.py lines 83–103: `leagues_to_score = list(df["League"].unique())` then `for league in leagues_to_score:` |
| MinMaxScaler fitted independently per league+position group, NOT across all leagues | 03-03 | ✅ verified | scorer.py lines 88–103: `league_df = df[df["League"] == league].copy()` passed to `_score_group`; test_per_league_normalization_isolation passes |
| scorer.compute_efficiency (UV regression) still operates on full pooled 5-league DataFrame | 03-03 | ✅ verified | scorer.py lines 123–153: compute_efficiency unchanged from Phase 2; no league loop; test_uv_regression_on_full_pool_multi_league passes |
| scorer.run_scoring_pipeline output preserves League column on every row | 03-03 | ✅ verified | merger.build_dataset assigns League per-league (line 405); pipeline passes it through; test_league_column_preserved_through_pipeline passes |
| test_scorer.py contains 3 new tests: test_per_league_normalization_isolation, test_uv_regression_on_full_pool_multi_league, test_league_column_preserved_through_pipeline | 03-03 | ✅ verified | test_scorer.py lines 149–369: all 3 tests present and fully implemented |
| all 3 new scorer tests pass (not skipped) | 03-03 | ✅ verified | Full test suite: 40 passed, 0 failures |

---

## Requirements Coverage

| Req ID | Definition | Plans | Status | Notes |
|--------|-----------|-------|--------|-------|
| DATA-01 | User can load player stats from FBref for all top 5 European leagues for 2024-25 and 2023-24 seasons | 03-01, 03-02, 03-03 | ✅ covered | FBREF_LEAGUES has 5 entries; run_fbref_scrapers loops all 5; build_dataset accepts {league: {season: ...}} |
| DATA-04 | System scrapes Transfermarkt market values for all clubs across all 5 leagues | 03-01 | ✅ covered | TM_LEAGUE_URLS with 5 wettbewerb codes; run_tm_scrapers loops all 5 leagues; _get_tm_club_list accepts league param |
| DATA-05 | System caches all scraped data with naming convention cache/fbref_{league}_{table}_{season}.csv and cache/tm_values_{league}_{season}.csv | 03-01 | ✅ covered | _fbref_cache_path uses `fbref_{league}_{table}_{season}.csv`; scrape_tm_season uses `tm_values_{league}_{season_label}` cache key |

**Notes on requirement scope:** DATA-01 also requires 2025-26 season support (per REQUIREMENTS.md). The ROADMAP traceability table assigns the multi-league component of DATA-01 to Phase 3; the 2025-26 season is excluded by design (mid-season, incomplete) per FBREF_SEASONS = ["2023-24", "2024-25"]. This is a known, intentional scope boundary — not a gap.

---

## Success Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| 1. Running python scraper.py populates cache files for all five leagues (40 FBref table files per season + five Transfermarkt files per season) | ⚠️ human_needed | Code structure is correct (run_fbref_scrapers loops 5 leagues × 9 tables × 2 seasons = 90 files; run_tm_scrapers loops 5 leagues × 2 seasons = 10 TM files). Cannot verify actual cache population without a live network scrape. |
| 2. The scored master DataFrame contains players from all five leagues, with a non-null League column on every row | ✅ verified | test_league_column_preserved_through_pipeline passes end-to-end with EPL + LaLiga synthetic data; build_dataset assigns League per league before concat; result["League"].notna().all() asserted |
| 3. Cache files follow naming convention cache/fbref_{league}_{table}_{season}.csv and cache/tm_values_{league}_{season}.csv; re-running within 7 days serves from cache | ✅ verified | _fbref_cache_path returns `fbref_{league}_{table}_{season}.csv`; scrape_tm_season cache_key = `tm_values_{league}_{season_label}`; test_cache_naming_new_leagues and test_tm_cache_naming_league_keyed both pass; 7-day TTL via _is_fresh() unchanged from Phase 1 |
| 4. MinMaxScaler normalization is fitted independently per league+position group — top-scored forward in La Liga and EPL both receive scout_score near 100 | ✅ verified | test_per_league_normalization_isolation passes: A1 (best LeagueA FW) > 80, B1 (best LeagueB FW) > 80; A3/B3 (worst in each) < 20 |

---

## Gaps

None. All must-haves from all three plans are present in the codebase with passing tests. One minor observation:

- The `TM_EPL_CLUBS_URL` constant has been removed from scraper.py as planned (confirmed by absence — not present in the file). The `TM_BASE` constant still exists (config.py line 111–114) but is no longer used by the active scraping path; it is dead code inherited from Phase 1. This is not a Phase 3 gap — it was not in-scope for removal in these plans.

---

## Human Verification Items

1. **Live scrape validation (Success Criterion 1):** Run `python scraper.py` on a machine with network access to confirm all 90 FBref cache files and 10 TM cache files are populated for 5 leagues × 2 seasons. The code is structurally correct and test-verified, but actual HTTP responses from fbref.com and transfermarkt.com have not been observed.

2. **TM wettbewerb code accuracy:** The five wettbewerb codes (GB1, ES1, L1, IT1, FR1) in TM_LEAGUE_URLS are sourced from Transfermarkt URL patterns. These were correct at plan authoring time (2026-03-17) but should be spot-checked against live Transfermarkt URLs if a scrape fails with 404 or redirect errors.
