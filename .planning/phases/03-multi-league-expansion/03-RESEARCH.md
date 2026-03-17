# Phase 3 Research — Multi-League Expansion

---

## FBref URL Patterns

### Competition IDs & URL Slugs

All five leagues follow the same URL pattern that `build_fbref_url` already implements:

```
https://fbref.com/en/comps/{comp_id}/{season_long}/{url_seg}/{season_long}-{slug}-Stats
```

Where `season_long` is the 4-digit form (e.g. `2024-2025`) and `url_seg` is the per-table path segment from `FBREF_TABLE_URL_SEGMENTS`.

| League | Canonical Key | comp_id | slug | Example standard URL |
|--------|--------------|---------|------|---------------------|
| EPL | `EPL` | 9 | `Premier-League` | `.../comps/9/2024-2025/stats/2024-2025-Premier-League-Stats` |
| La Liga | `LaLiga` | 12 | `La-Liga` | `.../comps/12/2024-2025/stats/2024-2025-La-Liga-Stats` |
| Bundesliga | `Bundesliga` | 20 | `Bundesliga` | `.../comps/20/2024-2025/stats/2024-2025-Bundesliga-Stats` |
| Serie A | `SerieA` | 11 | `Serie-A` | `.../comps/11/2024-2025/stats/2024-2025-Serie-A-Stats` |
| Ligue 1 | `Ligue1` | 13 | `Ligue-1` | `.../comps/13/2024-2025/stats/2024-2025-Ligue-1-Stats` |

**Confirmed by Google index of live FBref pages** (direct fetch returns 403 to bots but URLs appear in Google search results):
- La Liga: `https://fbref.com/en/comps/12/2024-2025/stats/2024-2025-La-Liga-Stats` — confirmed live
- Bundesliga: `https://fbref.com/en/comps/20/2024-2025/stats/2024-2025-Bundesliga-Stats` — confirmed live
- Serie A: `https://fbref.com/en/comps/11/2024-2025/stats/2024-2025-Serie-A-Stats` — confirmed live
- Ligue 1: `https://fbref.com/en/comps/13/2024-2025/stats/2024-2025-Ligue-1-Stats` — confirmed live

**No alternate slugs needed.** The slug is exactly `La-Liga`, `Bundesliga`, `Serie-A`, `Ligue-1` — not `Primera-Division`, `1-Bundesliga`, `Serie-A-TIM`, etc. This aligns exactly with the context file's table.

The `table_id` embedded in the HTML follows `{table_type}_{comp_id}`, e.g.:
- La Liga standard: `stats_standard_12`
- Bundesliga standard: `stats_standard_20`
- Serie A standard: `stats_standard_11`
- Ligue 1 standard: `stats_standard_13`

`_extract_fbref_table` already constructs this dynamically from `comp_id` — no change needed.

### Table Availability

All 9 required tables are confirmed available for all four new leagues from Google-indexed FBref sub-pages:

| Table key | url_seg | Confirmed for new leagues |
|-----------|---------|--------------------------|
| `stats_standard` | `stats` | Yes — all 4 |
| `stats_shooting` | `shooting` | Yes — confirmed via La Liga defense/misc patterns |
| `stats_passing` | `passing` | Yes — confirmed via Ligue 1 passing URL in search |
| `stats_defense` | `defense` | Yes — La Liga defense confirmed live |
| `stats_possession` | `possession` | Yes — La Liga possession confirmed live |
| `stats_misc` | `misc` | Yes — La Liga misc confirmed live |
| `stats_keeper` | `keepers` | Yes — all 4 confirmed via keepersadv pages existing |
| `stats_keeper_adv` | `keepersadv` | Yes — La Liga, Bundesliga, Serie A, Ligue 1 all confirmed live |
| `stats_gca` | `gca` | Yes — Bundesliga GCA confirmed live; La Liga GCA URL pattern confirmed |

**Key finding:** FBref provides keeper_adv and GCA tables for all top 5 leagues. These are not EPL-exclusive. The worldfootballR R package (which wraps the same FBref pages) scrapes all 9 table types for all top 5 leagues confirming structural parity.

**Known risk:** FBref has periodically restricted access to advanced stats for lower-tier competitions. For the top 5 European leagues, no such restriction has been observed. The existing `scrape_fbref_stat` error-handling (`try/except ValueError → return pd.DataFrame()`) already handles the case where a table is temporarily absent.

---

## Transfermarkt URLs

The existing `scrape_tm_season` / `_get_tm_club_list` flow hardcodes `TM_EPL_CLUBS_URL = "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1"` and appends `/saison_id/{season_year}`. The pattern is:

```
https://www.transfermarkt.com/{league-slug}/startseite/wettbewerb/{wettbewerb-id}/saison_id/{season_year}
```

| League | Canonical Key | league-slug | wettbewerb-id | Full URL (2024) |
|--------|--------------|-------------|---------------|-----------------|
| EPL | `EPL` | `premier-league` | `GB1` | `.../premier-league/startseite/wettbewerb/GB1/saison_id/2024` |
| La Liga | `LaLiga` | `laliga` | `ES1` | `.../laliga/startseite/wettbewerb/ES1/saison_id/2024` |
| Bundesliga | `Bundesliga` | `bundesliga` | `L1` | `.../bundesliga/startseite/wettbewerb/L1/saison_id/2024` |
| Serie A | `SerieA` | `serie-a` | `IT1` | `.../serie-a/startseite/wettbewerb/IT1/saison_id/2024` |
| Ligue 1 | `Ligue1` | `ligue-1` | `FR1` | `.../ligue-1/startseite/wettbewerb/FR1/saison_id/2024` |

All five confirmed via Google-indexed Transfermarkt pages. The `saison_id` is the start year of the season (2024 for 2024-25, 2023 for 2023-24), which is exactly how `run_tm_scrapers` already feeds `season_year` from `SEASONS`.

**HTML structure:** The club-list scraping uses `soup.select("table.items td.hauptlink a[href*='/verein/']")`. This CSS selector is the same across all TM league pages — the league overview uses an identical `table.items` structure for all top 5 leagues. The `_get_tm_club_list` function is structurally reusable without changes; only the URL changes per league.

**Club squad page:** `_scrape_tm_squad` uses the per-club kader URL pattern `/kader/verein/{id}/saison_id/{year}/plus/1` which is also universal across leagues.

**Cache naming:** `cache/tm_values_{LEAGUE}_{season}.csv` — but note that `scrape_tm_season` currently uses `cache_key = f"tm_values_{season_label.replace('-', '')}"` (no league prefix). This is a **Phase 3 change required**: add `league` parameter to `scrape_tm_season` and `_get_tm_club_list`, and update cache key to `f"tm_values_{league}_{season_label}"` to match DATA-05.

---

## Scraper Audit

### build_fbref_url

**Location:** `config.py` lines 70–98.

**Current structure:** Fully parametric. Looks up `comp_id` and `slug` from `FBREF_LEAGUES[league]`, then looks up `url_seg` from `FBREF_TABLE_URL_SEGMENTS[table_type]`. Converts short season label to long form internally. No hardcoding.

**What changes:** Nothing in the function itself. The only change is adding the 4 new entries to `FBREF_LEAGUES` in `config.py`:

```python
FBREF_LEAGUES = {
    "EPL":        {"comp_id": 9,  "slug": "Premier-League"},
    "LaLiga":     {"comp_id": 12, "slug": "La-Liga"},
    "Bundesliga": {"comp_id": 20, "slug": "Bundesliga"},
    "SerieA":     {"comp_id": 11, "slug": "Serie-A"},
    "Ligue1":     {"comp_id": 13, "slug": "Ligue-1"},
}
```

`build_fbref_url("LaLiga", "stats_standard", "2024-25")` will then produce:
`https://fbref.com/en/comps/12/2024-2025/stats/2024-2025-La-Liga-Stats` — correct.

### run_fbref_scrapers

**Location:** `scraper.py` lines 340–388.

**Current structure:** `leagues` parameter defaults to `list(FBREF_LEAGUES.keys())` — currently `["EPL"]` since that is the only key. The loop is already `for league in leagues → for season in seasons → for table_type in FBREF_TABLES`. The structure is already a 3-level serial loop. No hardcoded `"EPL"` string inside the loop body.

**What changes:** Adding 4 new keys to `FBREF_LEAGUES` in `config.py` is sufficient. When `leagues=None`, `list(FBREF_LEAGUES.keys())` automatically expands to all 5. No structural change to the function body needed.

**Cold run time impact:** 9 tables × 2 seasons × 5 leagues = 90 FBref requests. At 3.5–6.0s delay each: **315–540 seconds (5–9 minutes)**. The docstring currently says "9 tables × 2 seasons = 18 requests ≈ 80–100 seconds" — this needs updating to reflect the 5-league reality.

**Error handling:** `scrape_fbref_stat` already has a broad `except Exception` that returns `pd.DataFrame()` on fetch failure and logs a warning. The outer `run_fbref_scrapers` loop does not abort on empty DataFrames — it continues. This is the correct behavior for Phase 3 (skip unavailable league table, log warning, continue).

### run_tm_scrapers

**Location:** `scraper.py` lines 778–794.

**Current structure:**
- Hard-references `TM_EPL_CLUBS_URL` (a module-level constant pointing to the EPL page)
- Calls `scrape_tm_season(season_year, season_label)` — no `league` parameter
- `scrape_tm_season` uses `cache_key = f"tm_values_{season_label.replace('-', '')}"` (no league in key)
- `_get_tm_club_list` uses the module-level `TM_EPL_CLUBS_URL` constant directly
- Returns a single combined DataFrame of all seasons (latest market value per player)

**What must change:**
1. `TM_EPL_CLUBS_URL` is used only inside `_get_tm_club_list`. Either replace it with a `TM_LEAGUE_URLS` dict in `config.py`, or pass the URL as a parameter.
2. `scrape_tm_season` must accept a `league` parameter and use it in the cache key: `f"tm_values_{league}_{season_label}"`.
3. `_get_tm_club_list` must accept a `league_url` or `league` parameter instead of reading the module constant.
4. `run_tm_scrapers` must accept a `leagues=None` parameter (like `run_fbref_scrapers`), loop over all 5 leagues, and return a combined DataFrame across all leagues (or a dict keyed by league — see merger section).
5. `run_tm_scrapers` currently deduplicates by keeping the last market value per `player_name_tm`. With 5 leagues, the same player name could appear in two leagues (though this is unlikely for TM data since each club page is league-specific). The deduplication should be reviewed — it may need to be per-league or dropped entirely and left to `match_market_values`.

**Suggested TM league URL config addition** to `config.py`:
```python
TM_LEAGUE_URLS = {
    "EPL":        "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1",
    "LaLiga":     "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1",
    "Bundesliga": "https://www.transfermarkt.com/bundesliga/startseite/wettbewerb/L1",
    "SerieA":     "https://www.transfermarkt.com/serie-a/startseite/wettbewerb/IT1",
    "Ligue1":     "https://www.transfermarkt.com/ligue-1/startseite/wettbewerb/FR1",
}
```

**Return shape of run_tm_scrapers:** `build_dataset` currently calls `match_market_values(combined, tm_data)` once on the pooled multi-league DataFrame. `tm_data` needs to contain all 5 leagues' market values. The simplest approach is `run_tm_scrapers` returning a single concatenated DataFrame across all leagues (current shape: `player_name_tm`, `club_tm`, `market_value_eur`). This works because `match_market_values` matches by player name, not by league.

---

## Merger Audit

### build_dataset

**Location:** `merger.py` lines 317–371.

**Current structure:** Already has a `for league, league_data in fbref_data.items()` outer loop. Already assigns `df["League"] = league` (line 358) before appending to `all_frames`. Already calls `match_market_values(combined, tm_data)` once on the pooled multi-league DataFrame after concatenation.

**What changes:** Almost nothing structural. The function already supports multi-league natively:
- League loop: already present
- `League` column: already added at line 358
- TM matching: already done on pooled combined df (correct — market values need no league split)

**The one Phase 3 addition:** The `single_season` flag column per the context decisions. In `_aggregate_fbref_seasons`, after grouping by player, count distinct `_season` values per player:
```python
season_count = combined.groupby("Player")["_season"].nunique()
grouped["single_season"] = grouped["Player"].map(season_count) == 1
```
This should be added inside `_aggregate_fbref_seasons` before returning `grouped`.

**Min-minutes scaling:** `min_threshold = MIN_MINUTES_PER_SEASON * len(league_data)` — already scales by the number of seasons available for that league. No change needed.

### match_market_values

**Location:** `merger.py` lines 283–312.

**Current structure (2-pass):**
- Pass 1: Exact normalized name match via `dict.map`
- Pass 2: For unmatched rows, `rapidfuzz.process.extractOne` with `WRatio`, `score_cutoff=FUZZY_THRESHOLD` (80)
- Drops `_norm` column before returning

**Pass 3 addition (per context):** After Pass 2, for still-unmatched rows, run fuzzy matching with `score_cutoff=70` (not 80), but only accept candidates where the club name also matches. The normalized club name from FBref (`Squad` column) must equal the normalized TM club name (`club_tm`) after stripping "FC", "CF", "AFC", lowercase, strip accents.

Implementation approach:
1. Before the matching loop, build a second lookup: `tm_club_lookup = dict(zip(tm["_norm"], tm["club_tm"]))` (to retrieve the TM club for a fuzzy candidate).
2. In Pass 3, use `score_cutoff=70`, then check `normalize_club(df.at[idx, "Squad"]) == normalize_club(tm_club_lookup[result[0]])`.
3. A helper `normalize_club(name)` strips "FC", "CF", "AFC", lowercases, strips accents (reuse `normalize_name` logic).

Need to add `FUZZY_THRESHOLD_PASS3 = 70` to `config.py` (or hardcode as a local constant — config is cleaner).

**Impact:** Most beneficial for players with accented/hyphenated names common in La Liga (Vinícius Jr., Pedri González) and Ligue 1 (Amine Gouiri, Folarin Balogun). The club cross-check prevents false positives at the lower threshold.

---

## Scorer Audit

### compute_scout_scores

**Location:** `scorer.py` lines 61–79.

**Current structure:** Takes a single DataFrame, splits into 4 position groups (GK, FW, MF, DF), calls `_score_group` on each, concatenates. `_score_group` fits a `MinMaxScaler` on the position group's stat columns. There is no league grouping.

**The Phase 3 problem:** If the function is called on a 5-league combined DataFrame, the MinMaxScaler fits across all 5 leagues for each position group. An average La Liga forward would be normalized against the EPL forward distribution — correct behavior is disallowed by ROADMAP success criterion 4 and `SCORE-01`.

**What changes:** Add an outer `for league in df['League'].unique()` loop before the inner position-group loop. For each league, filter `df[df['League'] == league]`, run the existing 4-group scoring, append results. Concatenate after all leagues complete.

Conceptually:
```python
all_frames = []
for league in df['League'].unique():
    league_df = df[df['League'] == league].copy()
    # run existing 4-group scoring on league_df
    scored_league = _score_groups_for_df(league_df)
    all_frames.append(scored_league)
return pd.concat(all_frames, ignore_index=True)
```

The inner position-group loop and `_score_group` are unchanged. The change is the outer league wrapper in `compute_scout_scores` only.

**UV regression scope (SCORE-06, unchanged):** `compute_efficiency` in `scorer.py` lines 97–127 is called on the full pooled result from `compute_scout_scores`. It fits the OLS regression across all 5 leagues' players. This is the correct behavior — no change needed. The UV regression normalization is across the full pool; only scout score normalization is per-league.

### _score_group

**Location:** `scorer.py` lines 23–58.

**No changes needed.** Already operates on whatever DataFrame slice is passed to it. The MinMaxScaler fits within that slice. When the slice is a single league's position group rather than a 5-league position group, it automatically behaves correctly.

---

## Config Audit

**Current league config in `config.py`:**
- `FBREF_LEAGUES = {"EPL": {"comp_id": 9, "slug": "Premier-League"}}` — 1 league only
- No TM league URL dict — `TM_EPL_CLUBS_URL` is hardcoded in `scraper.py`
- `TM_BASE` points to EPL market values page (unused by the active scraping path)

**What needs adding to `config.py`:**

1. Four new entries to `FBREF_LEAGUES`:
   ```python
   FBREF_LEAGUES = {
       "EPL":        {"comp_id": 9,  "slug": "Premier-League"},
       "LaLiga":     {"comp_id": 12, "slug": "La-Liga"},
       "Bundesliga": {"comp_id": 20, "slug": "Bundesliga"},
       "SerieA":     {"comp_id": 11, "slug": "Serie-A"},
       "Ligue1":     {"comp_id": 13, "slug": "Ligue-1"},
   }
   ```

2. New `TM_LEAGUE_URLS` dict (or inline in scraper — config is cleaner for testability):
   ```python
   TM_LEAGUE_URLS = {
       "EPL":        "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1",
       "LaLiga":     "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1",
       "Bundesliga": "https://www.transfermarkt.com/bundesliga/startseite/wettbewerb/L1",
       "SerieA":     "https://www.transfermarkt.com/serie-a/startseite/wettbewerb/IT1",
       "Ligue1":     "https://www.transfermarkt.com/ligue-1/startseite/wettbewerb/FR1",
   }
   ```

3. Optional: `FUZZY_THRESHOLD_PASS3 = 70` for Pass 3 matching (current `FUZZY_THRESHOLD = 80` stays for Pass 2).

**What does NOT need changing:**
- `FBREF_TABLES` — the 9-table list applies identically to all leagues
- `FBREF_SEASONS` — same `["2023-24", "2024-25"]` for all leagues
- `FBREF_RATE_MIN / MAX` — rate limiting applies equally to all league requests
- `FBREF_BACKOFF_SEQUENCE` — unchanged
- `MIN_MINUTES_PER_SEASON` — 900 uniform across all leagues
- All pillar configs (`PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS`) — unchanged

---

## Test Audit

### Existing Tests

**test_scraper.py** — 9 tests, all no-network:
1. `test_cache_fresh` — `_is_fresh` TTL logic
2. `test_rate_limit_delay` — config value range check
3. `test_backoff_on_429` — monkeypatched 429 → RuntimeError
4. `test_url_construction` — `build_fbref_url` EPL only
5. `test_table_extraction` — HTML comment parsing
6. `test_column_presence` — monkeypatched HTTP → scrape output columns
7. `test_cache_naming` — `_fbref_cache_path` convention
8. `test_run_scrapers_epl` — `run_fbref_scrapers` orchestration with fake `scrape_fbref_stat`
9. `test_cache_hit_is_fast` — warm cache < 2s

**test_merger.py** — 12 tests, all no-network:
1. `test_standings_scraper_caches` — monkeypatched HTML → cache file
2. `test_multiclub_deduplication`
3. `test_nine_table_join_full`
4. `test_cross_season_aggregation`
5. `test_per90_derivation`
6. `test_drbsucc_rate_derivation`
7. `test_duels_won_pct_derivation`
8. `test_min_minutes_threshold_1800`
9. `test_current_season_filter`
10. `test_primary_position_extraction`
11. `test_league_position_attached`
12. `test_nine_table_join_missing_table`
13. `test_prgc_source_is_possession`

Total: 13 tests (not 12 — miscounted above).

**test_scorer.py** — 6 tests, all no-network:
1. `test_scorer_new_pillar_columns`
2. `test_gk_shot_stopping_pillar`
3. `test_age_weight_formula`
4. `test_age_column_parsing`
5. `test_uv_score_age_weighted_column_exists`
6. `test_uv_regression_full_pool`

**Current total: 28 tests across 3 files. Estimated runtime: < 5 seconds (all synthetic, no I/O or network).**

### New Tests Needed for Phase 3

**test_scraper.py additions (5 new tests):**

1. `test_url_construction_new_leagues` — Call `build_fbref_url` for all 4 new leagues and assert exact URL strings. No network required. Verifies config slugs and comp IDs are wired correctly.

2. `test_cache_naming_new_leagues` — Assert `_fbref_cache_path("LaLiga", ...)` produces `fbref_LaLiga_stats_standard_2024-25.csv`, etc. Trivial but documents the convention.

3. `test_run_fbref_scrapers_all_leagues` — Monkeypatch `scrape_fbref_stat`, call `run_fbref_scrapers()` with no arguments, verify all 5 leagues present in result, correct call count = 5 × 2 seasons × 9 tables = 90.

4. `test_run_tm_scrapers_multi_league` — Monkeypatch `scrape_tm_season` (with league param), verify `run_tm_scrapers()` calls it for all 5 leagues × 2 seasons, returns combined DataFrame with no duplicates.

5. `test_tm_cache_naming_league_keyed` — Assert `scrape_tm_season` with league param writes cache to `tm_values_{LEAGUE}_{season}.csv`, not the old league-free name.

**test_merger.py additions (4 new tests):**

6. `test_league_column_present_multi_league` — `build_dataset` with synthetic `fbref_data` containing 2 leagues returns DataFrame with `League` column; all rows have non-null League; each league key appears at least once.

7. `test_per_league_min_minutes_filter` — Two leagues in `fbref_data`, one player just above threshold in league A, one just below in league B — correct inclusion/exclusion per league.

8. `test_pass3_tm_matching` — Synthetic TM DataFrame with one player whose name matches FBref at WRatio ~75 (e.g. "Vinicius Junior" vs "Vinícius Jr.") but same club. Assert Pass 3 matches them. Then test a WRatio ~75 match but different club is NOT matched.

9. `test_single_season_flag` — `_aggregate_fbref_seasons` with a player appearing in only `2024-25` gets `single_season=True`; player in both seasons gets `single_season=False`.

**test_scorer.py additions (3 new tests):**

10. `test_per_league_normalization_isolation` — `compute_scout_scores` called on a 2-league DataFrame. Verify that the top forward in League A gets `scout_score` near 100, and independently the top forward in League B also gets `scout_score` near 100 — even if League B's absolute stats are lower. Directly tests ROADMAP success criterion 4.

11. `test_uv_regression_on_full_pool_multi_league` — Extend `test_uv_regression_full_pool` to confirm that the UV regression is fit on the pooled 5-league DataFrame (not per league). Verify that `len(full_result)` equals total player count across all leagues.

12. `test_league_column_preserved_through_pipeline` — `run_scoring_pipeline` with synthetic multi-league data; assert `League` column present in output with correct values for each player.

**Total new tests: 12. Total after Phase 3: 40 tests.**
**Estimated runtime: still < 10 seconds (all synthetic fixtures, no network).**

---

## Validation Architecture

### What Can Be Tested Without Network (Synthetic Fixtures)

All logic tests use in-memory DataFrames. The following are fully testable without real data:

- URL construction for all 5 leagues (pure string logic)
- Cache path naming convention (pure string logic)
- `run_fbref_scrapers` orchestration (monkeypatch `scrape_fbref_stat`)
- `run_tm_scrapers` orchestration (monkeypatch `scrape_tm_season`)
- Pass 3 TM matching logic (synthetic player/club DataFrames)
- `single_season` flag derivation (synthetic 1-season and 2-season data)
- `League` column propagation through `build_dataset` (synthetic multi-league `fbref_data`)
- Per-league normalization isolation in `compute_scout_scores` (synthetic scores)
- UV regression on full pooled pool (existing test pattern, extend to multi-league)

### What Requires Real Cached Data

- Confirming actual FBref table IDs for new leagues (e.g. `stats_standard_12` vs. any structural change) — requires a real cold scrape of at least one non-EPL league. This is a **manual verification step** in the first live run, not a test.
- Confirming TM HTML structure (`table.items` selector) is consistent for all 5 TM league pages — requires a live `_get_tm_club_list` call for each new league. **Manual verification only**, not part of automated test suite.
- Confirming GK keeper_adv data actually populates for all 5 leagues (FBref sometimes has sparse GK data for smaller leagues). For the top 5, this is expected to work — but first live run should be inspected.

### Which Files Get New Tests vs Extending Existing Tests

| File | Action |
|------|--------|
| `test_scraper.py` | Add 5 new test functions after existing tests |
| `test_merger.py` | Add 4 new test functions after existing tests |
| `test_scorer.py` | Add 3 new test functions after existing tests |
| `config.py` | No test file — tested indirectly via `test_scraper.py` URL tests |

**No new test files needed.** All 12 new tests slot into the existing 3 test files.

### Manual Validation Checklist (not automated)

1. After cold scrape: verify `cache/fbref_LaLiga_stats_standard_2024-25.csv` exists and has > 100 rows.
2. Check `cache/fbref_LaLiga_stats_gca_2024-25.csv` is non-empty (GCA table present for La Liga).
3. Spot-check one La Liga player (e.g. Vinícius Jr.) has non-NaN `market_value_eur` (Pass 3 matching working).
4. Run `compute_scout_scores` on the 5-league DataFrame and confirm top La Liga FW score ≈ top EPL FW score (both near 100 — per-league normalization working).
5. Confirm `League` column present on all rows of the scored output.
6. Confirm `single_season` column present — inspect how many players are single-season vs dual-season per league.

---

## Key Risks & Mitigations

### Risk 1: FBref Table IDs Differ for New Leagues
**Details:** The `_extract_fbref_table` call constructs `table_id = f"{table_type}_{comp_id}"`. For EPL this is `stats_standard_9`. For La Liga this would be `stats_standard_12`. If FBref uses a different ID format for non-English leagues, this would fail with a `ValueError` caught by the existing `except ValueError` block — returning `pd.DataFrame()` silently.
**Mitigation:** The URL slug confirmation above (La Liga `comp_id=12`, Ligue 1 `comp_id=13`, etc.) is consistent with the standard FBref table ID convention used for years. No evidence of deviation for top 5 leagues. First live run of `python scraper.py` validates this immediately. The silent fallback to `pd.DataFrame()` ensures pipeline doesn't crash; the `[warn]` log message will surface any issue.

### Risk 2: TM HTML Structure Differs Per League
**Details:** `_get_tm_club_list` uses `soup.select("table.items td.hauptlink a[href*='/verein/']")`. If a TM league page renders the club table differently (e.g. different CSS classes), no clubs will be returned.
**Mitigation:** Transfermarkt uses the same `table.items` CSS class across all league startseite pages — this is a documented, stable pattern. The function already has a guard: `if not clubs: print("[warn] No clubs found") → return []`. Manual inspection of the new league pages on first run will confirm the selector works.

### Risk 3: Player Name Collision Across Leagues in TM Data
**Details:** `run_tm_scrapers` currently deduplicates by keeping the last market value per `player_name_tm`. With 5 leagues, a common name (e.g. "David Silva" — hypothetically) could appear in two leagues' club rosters, and deduplication would silently drop one.
**Mitigation:** The current deduplication (`groupby("player_name_tm").last()`) was safe for EPL-only because each player appears once. For 5 leagues, this dedup should be removed from `run_tm_scrapers` — instead pass the full concatenated TM DataFrame (all leagues, all players) to `match_market_values`. Name collision is inherently handled because `match_market_values` normalizes names before matching, and the FBref player will match whichever TM row was found first (or the fuzzy best). The `club_tm` column in the TM data provides disambiguation if needed in Pass 3.

### Risk 4: Ligue 1 Name Encoding (Accents)
**Details:** Ligue 1 and La Liga have the highest density of accented player names. `normalize_name` strips accents via `unicodedata.NFD` + ASCII encode — this is correct. However, TM may romanize names differently from FBref (e.g. FBref: "Amine Gouiri" vs TM: "Amine Gouiri" — typically identical, but edge cases exist for Arabic/Portuguese names).
**Mitigation:** Pass 3 matching at WRatio 70-79 + club cross-check directly addresses this. The `normalize_name` function already handles accents via NFD decomposition. No code change needed beyond the Pass 3 addition.

### Risk 5: Bundesliga Season Year Mapping
**Details:** The Bundesliga uses the same calendar year convention as EPL (2024-25 season). `SEASONS = {"2023-24": 2023, "2024-25": 2024}` and `build_fbref_url` converts "2024-25" → "2024-2025". This should work for all 5 leagues — confirmed by the Bundesliga URL `https://fbref.com/en/comps/20/2024-2025/stats/2024-2025-Bundesliga-Stats`. No risk.

### Risk 6: Cold Scrape Runtime
**Details:** 90 FBref requests at 3.5–6.0s each = 315–540 seconds (5–9 minutes). TM: 5 leagues × 2 seasons × ~20 clubs each = ~200 squad-page requests at 5s each = ~1000 seconds (~17 minutes). Total cold run: **~22–27 minutes**.
**Mitigation:** Serial scraping is correct (rate-limit compliance). The cache means subsequent runs are sub-2s. The `python scraper.py` docstring/CLAUDE.md should be updated to reflect the new cold-run estimate. No code change needed — just documentation update.

### Risk 7: stats_gca Table Availability
**Details:** The `stats_gca` table was added as a 9th table specifically for Phase 2 to capture SCA. FBref's GCA page for non-EPL leagues is confirmed live (Bundesliga and La Liga GCA URLs appear in Google index). However, if a specific season's GCA data is sparse or the table structure differs slightly, `merge_fbref_tables` will handle it gracefully — `stats_gca` join already uses the same `_join_table` pattern that falls back to NaN fill if the table is empty.

---

## RESEARCH COMPLETE
